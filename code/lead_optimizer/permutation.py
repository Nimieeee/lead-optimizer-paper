from typing import List, Dict, Set, Optional
from itertools import product as cartesian_product
import logging
from rdkit import Chem
from .rdkit_engine import (
    execute_smirks_substitution,
    enforce_pharmacophore,
    calculate_sa_score,
    _ring_topology_profile,
)

logger = logging.getLogger(__name__)

_DEAD_SMIRKS_BY_TASK: Dict[str, Set[str]] = {}
_DEFAULT_TASK_KEY = "__default__"


def _get_dead_cache(task_id: Optional[str]) -> Set[str]:
    key = task_id or _DEFAULT_TASK_KEY
    return _DEAD_SMIRKS_BY_TASK.setdefault(key, set())


def clear_dead_smirks_cache(task_id: Optional[str] = None):
    """Clear the dead SMIRKS cache for a given task. Call this before each new optimization run.

    Without a task_id, only the default bucket is cleared, never wipe other concurrent tasks.
    """
    key = task_id or _DEFAULT_TASK_KEY
    if key in _DEAD_SMIRKS_BY_TASK:
        _DEAD_SMIRKS_BY_TASK[key].clear()
    logger.info(f"Cleared dead SMIRKS cache for task '{key}'")


def generate_combinatorial_library(
    lead_smiles: str,
    restricted_smarts_parts: List[str],
    strategies_by_site: Dict[int, List[Dict]],
    max_analogs: Optional[int] = None,
    task_id: Optional[str] = None,
) -> List[Dict]:
    """
    Combinatorial permutation + fragment expansion.

    strategies_by_site: {
        0: [{"smirks": "...", "name": "tetrazole"}, ...],
        1: [{"smirks": "...", "name": "pyridine"}, ...],
    }

    task_id scopes the dead-SMIRKS cache so concurrent optimization runs do not
    contaminate each other.
    """
    site_indices = sorted(strategies_by_site.keys())
    if not site_indices:
        logger.warning("No modification sites provided for combinatorial library")
        return []

    dead_cache = _get_dead_cache(task_id)

    # Pre-test individual SMIRKS against lead molecule to identify dead transformations
    dead_smirks = set()
    for site_idx in site_indices:
        for strat in strategies_by_site[site_idx]:
            smirks = strat.get("smirks", "")
            if smirks in dead_cache:
                dead_smirks.add(smirks)
                continue
            products = execute_smirks_substitution(lead_smiles, smirks)
            if not products:
                dead_smirks.add(smirks)
                dead_cache.add(smirks)
                name = strat.get("name", "unknown")
                logger.warning(f"SMIRKS pre-check: '{name}' (site {site_idx}) produced 0 valid products, skipping")

    if dead_smirks:
        logger.info(f"SMIRKS pre-check: {len(dead_smirks)} dead transformations skipped out of {sum(len(v) for v in strategies_by_site.values())} total")

    # Build per-site option lists (include "no change" option)
    site_options = []
    for idx in site_indices:
        options = [{"smirks": None, "name": "unchanged"}]
        for strat in strategies_by_site[idx]:
            if strat.get("smirks", "") not in dead_smirks:
                options.append(strat)
        site_options.append(options)
    
    # Cartesian product across all sites
    all_combinations = list(cartesian_product(*site_options))
    logger.info(f"Permutation: {len(all_combinations)} combinations from {len(site_indices)} sites (after dead SMIRKS filter)")
    
    # Cap to prevent combinatorial explosion (None = no cap)
    if max_analogs is not None and len(all_combinations) > max_analogs:
        logger.warning(f"Capping combinations from {len(all_combinations)} to {max_analogs}")
        all_combinations = all_combinations[:max_analogs]
    
    analogs = []
    lead_mol_for_profile = Chem.MolFromSmiles(lead_smiles)
    lead_profile = _ring_topology_profile(lead_mol_for_profile) if lead_mol_for_profile else (0, 0, 0)
    seen_smiles: Set[str] = {Chem.MolToSmiles(lead_mol_for_profile, canonical=True)} if lead_mol_for_profile else set()

    def _pick_best_product(products_list, target_profile):
        """When a SMIRKS produces multiple products (multi-instance matches),
        prefer the one whose ring topology matches the lead. Falls back to
        products[0] if none preserve topology (then enforce_pharmacophore
        filters it out anyway)."""
        if not products_list:
            return None
        if len(products_list) == 1 or not target_profile or target_profile == (0, 0, 0):
            return products_list[0]
        # Score each product by topology match
        for p in products_list:
            m = Chem.MolFromSmiles(p)
            if m and _ring_topology_profile(m) == target_profile:
                return p
        return products_list[0]

    for combo in all_combinations:
        # Skip "all unchanged" (the lead itself)
        if all(opt["smirks"] is None for opt in combo):
            continue

        current_smiles = lead_smiles
        modifications = []
        smirks_used = []

        # Apply SMIRKS sequentially for this combination. When a SMIRKS
        # produces multiple products (multi-instance), prefer the one that
        # preserves the lead's ring topology, this captures the user's
        # intent of "modify the decoration, not the scaffold" without
        # the exponential branching cost of fully exploring every product.
        valid = True
        for opt in combo:
            if opt["smirks"] is None:
                continue
            products = execute_smirks_substitution(current_smiles, opt["smirks"])
            if not products:
                valid = False
                break
            current_smiles = _pick_best_product(products, lead_profile) or products[0]
            mod_text = opt["name"]
            if opt.get("is_secondary"):
                mod_text = f"[Secondary] {mod_text}"
            rationale = opt.get("rationale", "")
            if rationale and rationale not in mod_text:
                mod_text += f": {rationale}"
            modifications.append(mod_text)
            smirks_used.append(opt["smirks"])

        if not valid:
            continue

        try:
            mol = Chem.MolFromSmiles(current_smiles)
            if mol is None:
                continue
            canonical = Chem.MolToSmiles(mol, canonical=True)
        except Exception:
            continue

        if canonical in seen_smiles:
            continue
        seen_smiles.add(canonical)

        # Pharmacophore check (hard: restricted SMARTS preserved; soft: ring
        # topology matches lead, allows methyl→ethyl on scaffold, rejects
        # ring-system destruction).
        if not enforce_pharmacophore(canonical, restricted_smarts_parts, lead_smiles=lead_smiles):
            continue
        
        # Synthesizability check via the unified synth_accessibility_service
        # (SYBA primary, SAScore fallback). Filter on the primary classifier:
        # drop analogs the model predicts as "Hard" with confidence.
        try:
            from app.services.simple_gasa_service import simple_gasa_predictor
            synth = simple_gasa_predictor.predict_single(canonical)
        except Exception:
            synth = None

        if not synth:
            continue
        # Discard clear-Hard analogs (syba_score < -25 means model is
        # confident the molecule is hard to synthesize; conservative cut).
        syba = synth.get("syba_score")
        sa_score = synth.get("sa_score")
        if syba is not None and syba < -25:
            continue
        # Defensive Ertl fallback when SYBA classifier was unavailable.
        if syba is None and sa_score is not None and sa_score > 6.0:
            continue

        analogs.append({
            "smiles": canonical,
            "modifications": modifications,
            "smirks_applied": smirks_used,
            "sa_score": sa_score,          # legacy Ertl, kept in record for audit
            "syba_score": syba,            # primary synth metric (signed; +=easier)
            "synth_prediction": synth.get("prediction"),
            "synth_interpretation": synth.get("interpretation"),
            "synth_confidence": synth.get("confidence"),
        })
    
    logger.info(f"Permutation: {len(analogs)} valid analogs generated")
    return analogs

def group_strategies_by_site(strategies: List[Dict]) -> Dict[int, List[Dict]]:
    """Helper to group a flat list of strategies into the format required by generator."""
    grouped = {}
    for s in strategies:
        site = s.get("site_index", 0)
        if site not in grouped:
            grouped[site] = []
        grouped[site].append(s)
    return grouped
