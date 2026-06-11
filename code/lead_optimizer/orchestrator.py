import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from rdkit import RDLogger
# Suppress ALL RDKit warnings (C++ and Python level)
RDLogger.DisableLog('rdApp.*')
from .schemas import (
    OptimizationResult, LeadProfile, VisionAgentOutput, 
    OptimizationAgentOutput, SmartsMapping, SmirksStrategy,
    ContextAnalysis
)
from .agents.vision_agent import run_vision_agent
from .agents.optimization_agent import run_optimization_agent
from .rdkit_engine import build_smarts_from_groups
from .profiler import profile_lead_compound
from .filtering import batch_prefilter
from .permutation import generate_combinatorial_library, group_strategies_by_site, clear_dead_smirks_cache
from .ranking import rank_analogs
from .diversity import select_diverse_representatives
from .context_analyzer import analyze_project_context
from .smirks_library import SMIRKS_LIBRARY

logger = logging.getLogger(__name__)

async def handle_vision_review(task_id: str, vision_output: VisionAgentOutput):
    """
    Store vision output and pause for user review.
    In this implementation, we assume the task is updated in the DB
    and the worker loop will check for 'awaiting_review' status.
    """
    from app.core.container import container
    db = container.get_db()
    
    # Update task status to awaiting_review
    try:
        db.table("optimization_tasks").update({
            "status": "awaiting_review",
            "current_stage": "vision_review",
            "stage_details": "Vision analysis complete. Awaiting user review.",
            "metadata": {
                "vision_output": vision_output.dict(),
                "awaiting_review": True,
            }
        }).eq("id", task_id).execute()
    except Exception as e:
        logger.error(f"Failed to update task for review: {e}")

def validate_strategies(
    strategies: List[SmirksStrategy],
    lead_smiles: str,
    smarts_mapping: SmartsMapping
) -> List[Dict]:
    """
    Validate LLM-proposed strategies before letting them into the analog library.

    Four gates (the last two are new — previously the validator only checked
    library-membership and site-bounds, which let the LLM propose strategies
    that silently failed at permutation time → fallback dominated the output):

    1. SMIRKS ID must exist in the curated library.
    2. site_index must be within the actual target_smarts list.
    3. The SMIRKS must execute against the lead (produces at least one product).
    4. The product must preserve the restricted pharmacophore (`enforce_pharmacophore`).
    """
    from .rdkit_engine import execute_smirks_substitution, enforce_pharmacophore

    validated = []
    seen = set()
    rejected = {"library": 0, "bounds": 0, "no_product": 0, "pharmacophore": 0}
    restricted_parts = [p for p in (smarts_mapping.restricted_smarts or "").split('.') if p]

    for s in strategies:
        if s.smirks_id not in SMIRKS_LIBRARY:
            rejected["library"] += 1
            continue

        if s.site_index < 0 or s.site_index >= len(smarts_mapping.target_smarts):
            rejected["bounds"] += 1
            continue

        # Execute the SMIRKS on the lead. If it produces zero valid products,
        # it'll fail the same way in permutation anyway — reject up-front so
        # downstream rationale strings don't accidentally surface dead SMIRKS.
        try:
            products = execute_smirks_substitution(lead_smiles, s.smirks)
        except Exception as exec_err:
            logger.debug(f"validate_strategies: SMIRKS {s.smirks_id} raised on execute ({exec_err}); rejecting")
            rejected["no_product"] += 1
            continue
        if not products:
            rejected["no_product"] += 1
            continue

        # Pharmacophore preservation — the LLM should not propose strategies
        # that obliterate the restricted (binding-essential) groups identified
        # by the Vision Agent. We only enforce this when restricted groups exist
        # (no-LID flow has none, in which case any product is acceptable).
        if restricted_parts:
            try:
                if not enforce_pharmacophore(products[0], restricted_parts, lead_smiles=lead_smiles):
                    rejected["pharmacophore"] += 1
                    continue
            except Exception as enforce_err:
                # Don't reject on enforcement crash — be permissive but log
                logger.debug(f"validate_strategies: enforce_pharmacophore raised for {s.smirks_id}: {enforce_err}")

        key = (s.site_index, s.smirks_id)
        if key in seen:
            continue
        seen.add(key)

        validated.append({
            "site_index": s.site_index,
            "smirks_id": s.smirks_id,
            "smirks": s.smirks,
            "name": s.replacement_name,
            "rationale": s.rationale,
            "predicted_impact": s.predicted_impact,
            "confidence": s.confidence,
            "is_fallback": False,
        })

    if any(rejected.values()):
        logger.info(
            f"validate_strategies: kept {len(validated)}/{len(strategies)} LLM strategies "
            f"(rejected: library={rejected['library']}, bounds={rejected['bounds']}, "
            f"no_product={rejected['no_product']}, pharmacophore={rejected['pharmacophore']})"
        )
    return validated

def deduplicate_strategies(strategies: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for s in strategies:
        key = (s["site_index"], s["smirks_id"])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def _fallback_strategies(smarts_mapping: SmartsMapping, seen: set, max_total: int = 40) -> List[Dict]:
    """
    Fallback: auto-select SMIRKS matching each target group to ensure coverage
    when the LLM's curated strategy list is sparse.

    Bounded to 5 matching entries per site (was 10) and confidence 0.4 (was 0.6)
    so curated LLM strategies (typical confidence 0.7-0.9) dominate the ranking
    instead of being drowned out by exhaustive fallback expansion. Tagged with
    is_fallback=True so downstream code can deprioritize.
    """
    from .smirks_library import get_smirks_for_group

    fallback = []
    for site_idx, group_name in enumerate(smarts_mapping.group_names):
        if len(fallback) + len(seen) >= max_total:
            break

        # group_name may be a per-instance label like "phenyl_left",
        # "aromatic_h_1", or "gem_dimethyl_central". The SMIRKS library is
        # keyed by BASE name (which may itself contain underscores —
        # `aromatic_h`, `gem_dimethyl`, `primary_amine`). Strip the
        # position-hint suffix progressively from the right until we hit
        # a known base name.
        matching = get_smirks_for_group(group_name)
        if not matching:
            parts = group_name.split("_")
            for cut in range(len(parts) - 1, 0, -1):
                candidate = "_".join(parts[:cut])
                trial = get_smirks_for_group(candidate)
                if trial:
                    matching = trial
                    logger.debug(f"SMIRKS lookup: '{group_name}' empty, base resolved to '{candidate}' ({len(matching)} entries)")
                    break
        # Cap to 5 per site (was 10) — fallback should fill gaps, not dominate
        for i, entry in enumerate(matching):
            if i >= 5:
                break
            if len(fallback) + len(seen) >= max_total:
                break

            key = (site_idx, entry.id)
            if key in seen:
                continue

            seen.add(key)
            fallback.append({
                "site_index": site_idx,
                "smirks_id": entry.id,
                "smirks": entry.smirks,
                "name": entry.name,
                "rationale": f"Auto-selected {entry.name} for {group_name}",
                "predicted_impact": entry.expected_impact,
                "confidence": 0.4,
                "is_fallback": True,
            })

    return fallback

async def batch_admet_screen(smiles_list: List[str]) -> List[Dict]:
    """Screen analogs using the ADMET service."""
    from app.core.container import container
    admet_service = container.get("admet_service")
    
    # Process in chunks of 50 to avoid overloading
    batch_size = 50
    all_results = []
    
    for i in range(0, len(smiles_list), batch_size):
        batch = smiles_list[i:i+batch_size]
        try:
            results = await admet_service.predict_batch(batch)
            all_results.extend(results)
        except Exception as e:
            logger.error(f"Batch ADMET failed: {e}")
            # Fill with empty results for failed batch
            all_results.extend([{} for _ in batch])
            
    return all_results

async def run_lead_optimization(
    lead_smiles: str,
    lid_diagram: bytes = None,
    user_context: str = "",
    target_analogs: int = 1000,
    visual_hints: str = "",
    progress_callback=None,
    task_id: str = None,
    vision_output: Optional[VisionAgentOutput] = None,
) -> OptimizationResult:
    """
    Main pipeline — plain async Python.
    If vision_output is provided, skips Stage 1 (Vision) and Stage 2 (Review).
    This is used when resuming a task after user review.
    """
    errors = []
    
    # Stage 1.5: RDKit Pre-Scan (always run)
    from .rdkit_engine import pre_scan_molecule
    scan_results = pre_scan_molecule(lead_smiles)
    detected_groups = scan_results['all']
    labeled_instances = scan_results.get('labeled', [])
    murcko_scaffold_atoms = scan_results.get('scaffold_atoms', set())
    murcko_scaffold_smarts = scan_results.get('scaffold_smarts', "")
    logger.debug(f"DEBUG: Stage 1.5 Pre-scan detected {len(detected_groups)} groups: {detected_groups}")
    logger.debug(f"DEBUG:   Core rings: {scan_results['core_rings']}")
    logger.debug(f"DEBUG:   Peripheral: {scan_results['peripheral']}")
    logger.debug(f"DEBUG:   Murcko scaffold: {len(murcko_scaffold_atoms)} atoms")
    
    # Determine if LID was provided
    has_lid = lid_diagram is not None
    
    if vision_output is None:
        # Stage 1: Vision Agent (only if not resuming from review)
        if lid_diagram:
            # Normal pipeline with LID
            if progress_callback:
                await progress_callback("vision", 5, "Analyzing ligand interaction diagram")
            
            vision_output = await run_vision_agent(
                lead_smiles, lid_diagram, visual_hints, detected_groups,
                progress_callback=progress_callback,
                labeled_instances=labeled_instances,
            )
            logger.debug(f"DEBUG: Stage 1 Vision Agent complete. Output groups: {len(vision_output.restricted_groups)} restricted, {len(vision_output.target_groups)} target")
            
            # Stage 2: User Review (pipeline pauses)
            if progress_callback:
                await progress_callback("vision_review", 10, "Awaiting user review")
            
            if task_id:
                logger.debug(f"DEBUG: Task ID {task_id} found. Pausing for review.")
                await handle_vision_review(task_id, vision_output)
                return None # Indicate pause
        else:
            # No LID provided — all groups are modifiable
            logger.info("DEBUG: No LID provided. Skipping Vision Agent. All functional groups will be modifiable.")
            if progress_callback:
                await progress_callback("vision", 5, "No LID provided. All functional groups modifiable.")
            
            # Create vision output with all groups as targets, none restricted
            from .schemas import ExposedGroup, FunctionalGroupInteraction
            vision_output = VisionAgentOutput(
                restricted_groups=[],
                target_groups=[
                    ExposedGroup(
                        group_name=g,
                        position_description=f"Detected by RDKit pre-scan",
                        modification_potential="high",
                        binding_affinity_impact="unknown"
                    )
                    for g in detected_groups
                ],
                overall_confidence=0.7
            )
            
            if progress_callback:
                await progress_callback("vision_review", 10, "No LID — all groups modifiable. Proceeding to ADMET profiling.")
    else:
        logger.info("DEBUG: Resuming pipeline with pre-computed vision output. Skipping Stage 1 & 2.")
        if progress_callback:
            await progress_callback("vision_review", 10, "Resuming with reviewed pharmacophore")
    
    logger.info("DEBUG: Stage 3: Entering SMARTS Builder...")
    # Stage 3: SMARTS Builder — receives Murcko scaffold so scaffold-embedded
    # decorations (e.g. methyl-on-scaffold) get auto-restricted, and the scaffold
    # SMARTS is appended to restricted_smarts as a pharmacophore anchor that
    # enforce_pharmacophore rejects any analog from breaking.
    smarts_mapping = build_smarts_from_groups(
        lead_smiles, vision_output, detected_groups,
        scaffold_atoms=murcko_scaffold_atoms,
        scaffold_smarts=murcko_scaffold_smarts,
        labeled_instances=labeled_instances,
    )
    logger.debug(f"DEBUG: SMARTS Builder complete. Mapping: {smarts_mapping.group_to_smarts}")
    
    # Stage 4: ADMET Profile
    if progress_callback:
        await progress_callback("admet_profile", 15, "Profiling lead compound")
    
    logger.info("DEBUG: Stage 4: Calling profile_lead_compound...")
    lead_profile = await profile_lead_compound(lead_smiles)
    logger.debug(f"DEBUG: Lead Profiling complete. MW={lead_profile.admet_data.get('molecular_weight')}")

    # Extract lead GASA hard probability for downstream use.
    # MUST happen here (right after lead profiling) — Stage 10.5 (GASA per-analog) reads this
    # variable, and previously it was defined later (after Stage 11), causing a NameError
    # that silently disabled per-analog GASA scoring and produced NaN SA Score deltas in
    # the report.
    lead_gasa_hard = 0.0
    lead_gasa = lead_profile.admet_data.get("GASA", {})
    if isinstance(lead_gasa, dict):
        lead_gasa_hard = lead_gasa.get("hard_probability", 0.0)

    # Compute lead SA score for report comparison AND inject the full
    # GASA dict (sa_score + easy/hard_probability + interpretation) into
    # lead_profile.admet_data["GASA"] so the frontend's per-analog vs
    # lead comparison table can read the lead's SA score the same way
    # it reads each analog's. Previously only `lead_sa_score` (scalar)
    # was kept and passed to the PDF generator — the UI showed NaN
    # because LeadProfile.admet_data["GASA"] had no sa_score field.
    # Compute lead synth-accessibility via the unified service. SYBA is
    # the primary classifier (signed: + easier, − harder); SAScore is
    # kept in the record for the audit trail but is NOT the displayed
    # metric. The report generator + frontend both render SYBA.
    lead_sa_score = None          # Ertl SAScore — kept for compatibility
    lead_syba_score = None        # SYBA primary
    try:
        from app.services.simple_gasa_service import simple_gasa_predictor
        sa_res = simple_gasa_predictor.predict_single(lead_smiles)
        if sa_res:
            lead_sa_score = sa_res.get("sa_score")
            lead_syba_score = sa_res.get("syba_score")
            existing_gasa = lead_profile.admet_data.get("GASA") or {}
            if not isinstance(existing_gasa, dict):
                existing_gasa = {}
            existing_gasa.setdefault("sa_score", sa_res.get("sa_score"))
            existing_gasa.setdefault("syba_score", sa_res.get("syba_score"))
            existing_gasa.setdefault("easy_probability", sa_res.get("easy_probability"))
            existing_gasa.setdefault("hard_probability", sa_res.get("hard_probability"))
            existing_gasa.setdefault("prediction", sa_res.get("prediction"))
            existing_gasa.setdefault("interpretation", sa_res.get("interpretation"))
            existing_gasa.setdefault("primary_method", sa_res.get("primary_method"))
            existing_gasa.setdefault("confidence", sa_res.get("confidence"))
            lead_profile.admet_data["GASA"] = existing_gasa
    except Exception as e:
        logger.warning(f"⚠️ Lead synth-accessibility calculation failed: {e}")
    
    # Stage 5: Context Analyzer
    if progress_callback:
        await progress_callback("context_analysis", 20, "Analyzing project context for ADMET priorities")
    
    logger.info("DEBUG: Stage 5: Calling analyze_project_context...")
    context_analysis = await analyze_project_context(
        user_context=user_context,
        lead_liabilities=[l.dict() for l in lead_profile.liabilities],
        lead_smiles=lead_smiles,
    )
    logger.info("DEBUG: Context analysis complete.")
    
    # Stage 6: Optimization Agent
    if progress_callback:
        await progress_callback("optimization", 25, "Evaluating bioisosteric replacement strategies")
    
    # Construct a multi-objective goal summarize top liabilities
    top_liabilities = lead_profile.liabilities[:3]
    if top_liabilities:
        multi_goal = "Solve critical liabilities: " + ", ".join([f"{l.endpoint} ({l.direction})" for l in top_liabilities])
    else:
        multi_goal = "General ADMET optimization"
        
    lead_profile.primary_goal = multi_goal # Update for agent visibility

    opt_output = None
    try:
        opt_output = await run_optimization_agent(
            lead_smiles, vision_output, lead_profile, user_context
        )
        llm_strategies = opt_output.strategies
    except Exception as e:
        logger.error(f"❌ Optimization Agent failed: {e}. Using fallback strategies only.")
        llm_strategies = []
    
    # Stage 7: Critic
    validated = validate_strategies(llm_strategies, lead_smiles, smarts_mapping)
    
    # ── Strategy Selection: AI + Fallback ──
    # LLM selects intelligently, then fallback auto-selects matching SMIRKS to ensure coverage
    seen_keys = {(s["site_index"], s["smirks_id"]) for s in validated}
    
    # Apply fallback to ensure comprehensive coverage
    # With LID: limit to 50 (Vision Agent provides intelligent selection, less fallback needed)
    # Without LID: up to 100 (need more fallback coverage since no strategic guidance)
    if progress_callback:
        await progress_callback("optimization", 30, f"Selected {len(validated)} strategies. Expanding coverage...")
    
    # Fallback ceiling — lowered from 50/100 to 20/40 so curated LLM strategies
    # dominate the analog mix. Per-site cap is enforced inside _fallback_strategies (5).
    fallback_limit = 20 if has_lid else 40
    fallback = _fallback_strategies(smarts_mapping, seen_keys, max_total=fallback_limit)
    if fallback:
        validated.extend(fallback)
        validated = deduplicate_strategies(validated)
    
    logger.debug(f"DEBUG: Final strategy count: {len(validated)} (LLM: {len(seen_keys)}, Fallback: {len(fallback)})")
    
    # Stage 8: Permutation
    # Clear dead SMIRKS cache for this run (prevent cross-contamination between molecules)
    clear_dead_smirks_cache(task_id)
    
    if progress_callback:
        # Pre-emit the site-count estimate so the FE shows "expanding from N sites"
        # before the (potentially long) permutation runs.
        _pre_sites = len({s.get("site_index") for s in validated if s.get("site_index") is not None})
        await progress_callback(
            "permutation", 40,
            f"Generating combinatorial library from {len(validated)} strategies across {_pre_sites} editable site"
            f"{'s' if _pre_sites != 1 else ''}…"
        )
    
    # Always cap to 100K — LID constrains sites but secondary targets can still inflate combinations
    max_analogs = 100000
    restricted_parts = [p for p in smarts_mapping.restricted_smarts.split('.') if p]
    
    # Secondary targets: unlock only the weakest restricted group for conservative modification
    secondary_targets = []
    secondary_strategies = []
    if has_lid and vision_output.restricted_groups:
        restricted_count = len(vision_output.restricted_groups)
        # Only unlock the single weakest interaction (lowest confidence) to prevent site inflation
        unlock_count = 1
        
        # Sort by interaction confidence (weakest first = safer to modify)
        sorted_restricted = sorted(
            vision_output.restricted_groups,
            key=lambda g: g.confidence
        )
        
        for group in sorted_restricted[:unlock_count]:
            # Display all contacting residues, not just the first one — multi-residue
            # groups must show every interaction they make.
            residue_label = ", ".join(group.residues) if group.residues else (group.residue or "unknown")
            secondary_targets.append({
                "group_name": group.group_name,
                "reason": f"Weak {group.interaction_type.value} with {residue_label}",
                "is_secondary": True
            })
            # Find matching SMIRKS for this group (conservative only)
            from .rdkit_engine import is_conservative_smirks
            from .smirks_library import get_smirks_for_group
            matching = get_smirks_for_group(group.group_name)
            # Try conservative SMIRKS first
            conservative_matches = [e for e in matching if is_conservative_smirks(e.id)]
            # If no conservative matches, use ALL matches (better than 0 alternatives)
            matches_to_use = conservative_matches if conservative_matches else matching[:10]
            for entry in matches_to_use:
                secondary_strategies.append({
                    "site_index": len(smarts_mapping.target_smarts) + len(secondary_targets) - 1,
                    "smirks_id": entry.id,
                    "smirks": entry.smirks,
                    "name": entry.name,
                    "rationale": f"Conservative modification of restricted {group.group_name}",
                    "predicted_impact": entry.expected_impact,
                    "confidence": 0.5,
                    "is_secondary": True
                })
    
    # Site count = distinct site_index values across all strategies.
    # Reported to the FE so the chemist can see how many editable
    # positions the permutation actually exercised.
    all_strategies = validated + secondary_strategies
    site_count = len({s.get("site_index") for s in all_strategies if s.get("site_index") is not None})

    analogs_raw = generate_combinatorial_library(
        lead_smiles, restricted_parts,
        group_strategies_by_site(all_strategies),
        max_analogs=max_analogs,
        task_id=task_id,
    )

    # Surface the search-space numbers to the FE so the chemist can see
    # the permutation actually did real work. stage_details lands directly
    # in the PipelineMonitor hero card.
    if progress_callback:
        await progress_callback(
            "permutation", 50,
            f"Permutation complete: {len(analogs_raw):,} valid analogs from {site_count} editable site"
            f"{'s' if site_count != 1 else ''} × {len(all_strategies)} strategies"
        )

    # Stage 9: Pre-Filter
    if progress_callback:
        await progress_callback(
            "filtering", 55,
            f"Pre-filtering {len(analogs_raw):,} candidates (Lipinski + PAINS + Brenk + Glaxo)"
        )

    filtered_res = batch_prefilter([a['smiles'] for a in analogs_raw])
    passing_analogs = []
    for a, (smi, passed, details) in zip(analogs_raw, filtered_res):
        if passed:
            a["filter_results"] = details
            passing_analogs.append(a)

    # Emit the pre-filter result count so the user sees how many made it
    # through to the expensive ADMET stage.
    if progress_callback and analogs_raw:
        pct = (len(passing_analogs) / len(analogs_raw)) * 100
        await progress_callback(
            "filtering", 60,
            f"Pre-filter: {len(passing_analogs):,}/{len(analogs_raw):,} passed ({pct:.1f}%)"
        )

    # Stage 10: Batch ADMET
    if progress_callback:
        await progress_callback("admet_screen", 70, f"ADMET screening {len(passing_analogs):,} analogs")
    
    admet_results = await batch_admet_screen([a['smiles'] for a in passing_analogs])
    for a, res in zip(passing_analogs, admet_results):
        a["admet_results"] = res
    
    # Stage 10.5: GASA Synthetic Accessibility (per-analog)
    if progress_callback:
        await progress_callback("admet_screen", 75, f"Assessing synthetic accessibility for {len(passing_analogs)} analogs")
    
    try:
        from app.services.gasa_service import gasa_predictor
        from app.services.simple_gasa_service import simple_gasa_predictor
        
        # Fallback to simple GASA if lead scaffold is ML=Hard but RDKit=Easy
        # ML GASA is unreliable for scaffolds it hasn't seen in training (e.g., chromenes)
        use_simple_gasa = False
        if lead_gasa_hard > 0.5 and lead_sa_score is not None and lead_sa_score < 4.0:
            logger.warning(f"⚠️ Lead GASA ML=Hard ({lead_gasa_hard:.2f}) but RDKit SA=Easy ({lead_sa_score:.2f}). Using simple GASA for all analogs.")
            use_simple_gasa = True
        
        for a in passing_analogs:
            smiles = a["smiles"]
            gasa_result = None
            
            if use_simple_gasa:
                try:
                    gasa_result = simple_gasa_predictor.predict_single(smiles)
                except Exception:
                    pass
            else:
                try:
                    gasa_result = gasa_predictor.predict_single(smiles)
                except Exception:
                    pass
                
                if not gasa_result:
                    try:
                        gasa_result = simple_gasa_predictor.predict_single(smiles)
                    except Exception:
                        pass
            
            if gasa_result:
                if "admet_results" not in a:
                    a["admet_results"] = {}
                a["admet_results"]["GASA"] = gasa_result
                a["gasa_score"] = gasa_result.get("hard_probability", 0.5)
    except Exception as e:
        logger.warning(f"⚠️ GASA per-analog failed (non-critical): {e}")
    
    # Stage 11: Diversity + Ranking
    if progress_callback:
        await progress_callback("ranking", 85, "Context-aware diversity analysis and ranking")
    
    # Calculate diversity bonus and tanimoto scores for ranking
    from rdkit import DataStructs
    from rdkit.Chem import AllChem, MolFromSmiles
    lead_mol = MolFromSmiles(lead_smiles)
    lead_fp = AllChem.GetMorganFingerprintAsBitVect(lead_mol, 2, 2048)
    
    tanimoto_scores = []
    for a in passing_analogs:
        mol = MolFromSmiles(a["smiles"])
        if mol:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, 2048)
            sim = DataStructs.TanimotoSimilarity(fp, lead_fp)
            tanimoto_scores.append(sim)
        else:
            tanimoto_scores.append(0.0)
    
    # lead_gasa_hard was extracted right after lead profiling — used by both Stage 10.5
    # (per-analog GASA, line ~398) and here for ranking.
    # lead_smiles is now passed so rank_analogs can compute Murcko scaffold preservation
    # and hard-stop drastic scaffold blowups (aromatic → aliphatic kinase-inhibitor scaffolds).
    ranked = rank_analogs(
        passing_analogs,
        lead_profile.admet_data,
        context_analysis,
        tanimoto_scores,
        user_context,
        lead_gasa_hard,
        lead_smiles=lead_smiles,
    )
    diverse_top = select_diverse_representatives(ranked, lead_smiles, max_per_cluster=10)
    
    # Stage 12: Report - Build methodology notes FIRST (before generate_report)
    methodology_notes_list = []
    if has_lid:
        methodology_notes_list.append(f"LID Analysis: {len(vision_output.restricted_groups)} restricted groups, {len(vision_output.target_groups)} target groups identified.")
        if secondary_targets:
            methodology_notes_list.append(f"Secondary Targets: {len(secondary_targets)} restricted groups unlocked for conservative modification.")
        methodology_notes_list.append(f"Search Space: {len(analogs_raw)} combinations from {len(validated)} primary strategies.")
    else:
        methodology_notes_list.append("No LID provided. All detected functional groups treated as modifiable targets.")
        methodology_notes_list.append(f"Expanded Search Space: {len(analogs_raw)} combinations tested (cap: 15,000).")
    
    methodology_text = " ".join(methodology_notes_list)
    
    if progress_callback:
        await progress_callback("report", 95, "Generating PhD-grade report and files")
    
    from .report_generator import generate_report
    report_paths = await generate_report(
        lead_smiles, lead_profile, diverse_top, vision_output, user_context, context_analysis,
        expert_narrative=(opt_output.expert_narrative if opt_output else None) or "Strategy selection completed",
        used_lid=has_lid,
        secondary_targets=secondary_targets,
        search_space_size=len(analogs_raw),
        methodology_notes=methodology_text,
        lead_sa_score=lead_sa_score,
        lead_syba_score=lead_syba_score
    )
    
    if progress_callback:
        await progress_callback("done", 100, "Complete")
    
    from .schemas import AnalogRecord, FilterResults
    final_analogs = []
    for a in diverse_top[:50]:
        fr = a.get("filter_results", {})
        if isinstance(fr, dict):
            fr_model = FilterResults(**fr)
        else:
            fr_model = fr
            
        final_analogs.append(AnalogRecord(
            smiles=a["smiles"],
            canonical_smiles=a["smiles"],
            lead_smiles=lead_smiles,
            modifications=a.get("modifications", []),
            smirks_applied=[],
            agent_rationale=(opt_output.expert_narrative if opt_output else None) or "Multi-objective optimization",
            rag_chunks_used=[],
            sa_score=a.get("sa_score", 3.0),
            filter_results=fr_model,
            admet_results=a.get("admet_results"),
            pareto_rank=a.get("pareto_rank"),
            pareto_score=a.get("pareto_score")
        ))


    
    return OptimizationResult(
        lead_profile=lead_profile,
        total_strategies=len(validated) + len(secondary_strategies),
        total_analogs_generated=len(analogs_raw),
        total_passed_prefilter=len(passing_analogs),
        total_passed_admet=len([a for a in passing_analogs if a.get("admet_results")]),
        top_analogs=final_analogs,
        diversity_clusters=len(diverse_top),
        report_pdf_path=report_paths["pdf"],
        sdf_path=report_paths["sdf"],
        iterations_used=1,
        errors=[],
        used_lid=has_lid,
        secondary_targets=secondary_targets,
        search_space_size=len(analogs_raw),
        methodology_notes=methodology_text
    )
