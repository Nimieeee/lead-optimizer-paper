"""
Multi-objective ranking using LLM-derived endpoint weights + GASA synthetic accessibility.
"""

from typing import List, Dict, Optional
import logging
from .schemas import ContextAnalysis
from .admet_metadata import get_endpoint_direction

logger = logging.getLogger(__name__)

# Base weights for non-ADMET objectives (always applied)
# Total: 0.65 for ADMET + 0.35 for these = 1.00
BASE_WEIGHTS = {
    "scaffold_preservation": 0.15,     # Murcko match — hard-stops aromatic-to-aliphatic blowups
    "pharmacophore_similarity": 0.05,  # Tanimoto Morgan fingerprint (topology, not scaffold)
    "gasa_accessibility": 0.05,        # Synthesis difficulty
    "diversity_bonus": 0.05,
    "drug_likeness": 0.05,
}
# Total non-ADMET = 0.35; ADMET = 0.65


def _get_synth_difficulty(analog_admet: Dict) -> float:
    """Return synthetic-accessibility difficulty in [0, 1] where higher = harder.

    Audit phase 5 (2026-06-06): SYBA is the platform-ratified primary metric
    (Voršilák 2020, AUC > 0.81). SYBA's signed score [-50, +50] is mapped to
    a difficulty probability via a sigmoid centred at 0. Falls back to the
    legacy `hard_probability` only when SYBA isn't available, and to a neutral
    0.0 when no GASA dict at all (don't penalise unknown).
    """
    gasa = analog_admet.get("GASA")
    if not isinstance(gasa, dict):
        return 0.0
    syba = gasa.get("syba_score")
    if isinstance(syba, (int, float)):
        # Sigmoid centred at 0 → maps -25 to ~0.08 (easy), +25 to ~0.92 (hard)
        # if we invert sign. SYBA convention: positive = EASIER, so flip sign
        # to get "difficulty".
        import math
        return 1.0 / (1.0 + math.exp(syba / 8.0))
    # Fallback: legacy hard_probability if SYBA is missing (older records).
    return float(gasa.get("hard_probability", 0.0))


# Back-compat alias — old call sites referenced `_get_gasa_hard_prob`. Returns
# the same difficulty signal; both names point at the same SYBA-first logic.
_get_gasa_hard_prob = _get_synth_difficulty


def _murcko_scaffold_match(lead_smiles: str, analog_smiles: str) -> float:
    """
    Score how much of the lead's Murcko scaffold the analog preserves.

    Returns:
        1.0 = identical scaffold (Murcko canonical SMILES match)
        Tanimoto in (0.0, 1.0) = partial preservation (Morgan fingerprint of scaffold)
        0.0 = scaffold computation failed for either side
    """
    if not lead_smiles or not analog_smiles:
        return 0.5  # Unknown — neutral
    try:
        from rdkit import Chem, DataStructs
        from rdkit.Chem import AllChem
        from rdkit.Chem.Scaffolds import MurckoScaffold

        lead_mol = Chem.MolFromSmiles(lead_smiles)
        analog_mol = Chem.MolFromSmiles(analog_smiles)
        if lead_mol is None or analog_mol is None:
            return 0.5

        lead_scaffold = MurckoScaffold.GetScaffoldForMol(lead_mol)
        analog_scaffold = MurckoScaffold.GetScaffoldForMol(analog_mol)
        if lead_scaffold is None or analog_scaffold is None:
            return 0.5

        lead_scaffold_smi = Chem.MolToSmiles(lead_scaffold)
        analog_scaffold_smi = Chem.MolToSmiles(analog_scaffold)
        if not lead_scaffold_smi or not analog_scaffold_smi:
            return 0.5

        if lead_scaffold_smi == analog_scaffold_smi:
            return 1.0

        # Different scaffolds — compute Morgan Tanimoto over the scaffold mols
        # so we still credit "phenyl swap" (partial preservation) vs "phenyl→cyclohexyl"
        # (full aromaticity loss, much lower Tanimoto).
        try:
            lead_fp = AllChem.GetMorganFingerprintAsBitVect(lead_scaffold, 2, 1024)
            analog_fp = AllChem.GetMorganFingerprintAsBitVect(analog_scaffold, 2, 1024)
            return DataStructs.TanimotoSimilarity(lead_fp, analog_fp)
        except Exception:
            return 0.0
    except Exception as scaffold_err:
        logger.debug(f"Murcko scaffold match failed for analog {analog_smiles[:40]}...: {scaffold_err}")
        return 0.5


def _flag_implausible_admet(analog_admet: Dict, lead_admet: Dict) -> bool:
    """
    Sanity check: if more than 4 ADMET endpoints simultaneously improve by >80%,
    the ADMET model is likely returning low-confidence point estimates for an
    out-of-distribution scaffold. Flag the analog so the UI can warn.
    """
    if not analog_admet or not lead_admet:
        return False
    huge_improvements = 0
    for ep in ("hERG", "AMES", "DILI", "CYP1A2_Veith", "CYP2C9_Veith", "CYP2C19_Veith", "CYP2D6_Veith", "CYP3A4_Veith"):
        lead_v = lead_admet.get(ep)
        analog_v = analog_admet.get(ep)
        if lead_v is None or analog_v is None:
            continue
        try:
            lead_v = float(lead_v)
            analog_v = float(analog_v)
        except (TypeError, ValueError):
            continue
        if lead_v <= 0.05:
            continue  # Lead already near floor — improvement % is meaningless
        improvement = (lead_v - analog_v) / lead_v
        if improvement > 0.80:
            huge_improvements += 1
    return huge_improvements > 4


def calculate_pareto_score(
    analog: Dict,
    lead_admet: Dict,
    context_analysis: ContextAnalysis,
    tanimoto_to_lead: float = 0.0,
    user_context: str = "",
    lead_gasa_hard: float = 0.0,
    lead_smiles: str = ""
) -> float:
    """
    Calculate a weighted multi-objective score using LLM-derived weights + GASA + scaffold preservation.

    NOTE: This ranking does NOT include binding affinity / target potency. Scaffold
    preservation (Murcko match, weight 0.15) acts as a proxy: drastic scaffold changes
    (aromatic → aliphatic, ring count change) are penalised on the assumption that they
    likely break binding. True binding-pose evaluation requires a docking step that is
    not yet wired into the pipeline.
    """
    analog_admet = analog.get("admet_results", {})
    analog_smiles = analog.get("smiles", "")

    # ── Scaffold preservation (Murcko match) ────────────────────
    # Hard-stop: if the analog's Murcko scaffold has zero Tanimoto similarity to the
    # lead's (e.g. phenyl → cyclohexyl flips aromaticity completely), cap the final
    # pareto score at 0.30 even if ADMET looks great. This prevents pharmacophore-
    # destroying transformations from ranking #1.
    scaffold_score = _murcko_scaffold_match(lead_smiles, analog_smiles) if lead_smiles else 0.5
    scaffold_destroyed = scaffold_score < 0.1

    # ── Implausible ADMET sanity flag ──────────────────────────
    # Tagged on the analog dict for FE display; doesn't change scoring but warns the
    # user when the model is likely returning low-confidence predictions for an out-
    # of-distribution scaffold.
    if _flag_implausible_admet(analog_admet, lead_admet):
        analog["_admet_implausible"] = True
    
    # ── GASA Hard-Stop (Synthetic Accessibility) ────────────────
    # Relative penalty: only penalize if analog is HARDER than the lead compound
    gasa_hard_prob = _get_gasa_hard_prob(analog_admet)
    gasa_penalty = 1.0
    if gasa_hard_prob > 0.5:
        # Only penalize if analog is meaningfully harder than lead (10% tolerance)
        if lead_gasa_hard > 0:
            harder_by = gasa_hard_prob - lead_gasa_hard
            if harder_by > 0.10:
                gasa_penalty = max(0.3, 1.0 - (harder_by - 0.10) * 1.4)
        else:
            # No lead reference — use absolute threshold
            gasa_penalty = max(0.3, 1.0 - (gasa_hard_prob - 0.5) * 1.4)
    
    # ── ADMET Improvement Score (context-weighted) ──────────────
    # CNS boost: if context mentions brain/CNS, give BBB 1.5x weight
    cns_keywords = ['cns', 'brain', 'neuro', 'alzheimer', 'parkinson', 'epilepsy',
                     'stroke', 'glioma', 'cognitive', 'dementia', 'down syndrome',
                     'huntington', 'amyotrophic', 'central nervous']
    is_cns_target = any(kw in user_context.lower() for kw in cns_keywords) if user_context else False
    
    if not analog_admet:
        admet_score = 0.5  # Neutral fallback if no ADMET data
    else:
        admet_score = 0.0
        total_weight = 0.0
        critical_worsened = False  # Track if any critical endpoint got worse
        
        for priority in context_analysis.endpoint_priorities:
            ep = priority.endpoint
            weight = priority.weight
            
            # Boost BBB for CNS targets
            if ep == 'BBB_Martins' and is_cns_target:
                weight = min(1.0, weight * 1.5)
            
            direction = get_endpoint_direction(ep)
            
            if weight == 0.0:
                continue
            
            lead_val = lead_admet.get(ep)
            analog_val = analog_admet.get(ep)
            
            if lead_val is None or analog_val is None:
                continue
            
            # Calculate fractional improvement
            if direction == "reduce":
                if lead_val > 0.01:
                    improvement = (lead_val - analog_val) / lead_val
                else:
                    improvement = 0.0
            else:
                if lead_val > 0.01:
                    improvement = (analog_val - lead_val) / lead_val
                elif analog_val > 0.01:
                    improvement = 1.0
                else:
                    improvement = 0.0
            
            # Clamp to [-1, 1] and shift to [0, 1]
            improvement = max(-1.0, min(1.0, improvement))
            normalized = (improvement + 1.0) / 2.0
            
            # 75% penalty for worsening ANY liability
            if improvement < 0:
                normalized *= 0.25     # 75% penalty
                if weight > 0.3:       # If it's a high-priority endpoint
                    critical_worsened = True
            
            # BBB floor penalty for CNS targets: CNS drugs MUST cross BBB
            if ep == 'BBB_Martins' and is_cns_target:
                analog_bbb = analog_val
                if analog_bbb < 0.5:
                    gasa_penalty *= 0.5  # 50% score reduction for poor BBB in CNS context
            
            admet_score += normalized * weight
            total_weight += weight
        
        if total_weight > 0:
            admet_score /= total_weight
        else:
            admet_score = 0.5
        
        # Cap score if any critical liability worsened significantly
        if critical_worsened:
            admet_score = min(admet_score, 0.6)
    
    # ── Non-ADMET Objectives ────────────────────────────────────
    scores = {"admet_improvement": admet_score}
    scores["scaffold_preservation"] = scaffold_score
    scores["pharmacophore_similarity"] = tanimoto_to_lead
    
    # GASA accessibility score (relative to lead)
    # Easier than lead → 1.0, Same as lead → 1.0, Harder → decreases proportionally
    if lead_gasa_hard > 0:
        harder_by = max(0.0, gasa_hard_prob - lead_gasa_hard)
        scores["gasa_accessibility"] = max(0.0, 1.0 - harder_by)
    else:
        scores["gasa_accessibility"] = 1.0 - gasa_hard_prob
    
    # Drug-likeness
    filter_results = analog.get("filter_results", {})
    if isinstance(filter_results, dict):
        violations = filter_results.get("lipinski_details", {}).get("violations", 0)
        scores["drug_likeness"] = max(0.0, 1.0 - violations * 0.25)
    else:
        scores["drug_likeness"] = 0.5
    
    scores["diversity_bonus"] = analog.get("diversity_bonus", 0.5)
    
    # ── Weighted Combination ────────────────────────────────────
    admet_weight = 0.65  # Pharmacology matters more than synthesis difficulty
    total = scores["admet_improvement"] * admet_weight

    for obj, weight in BASE_WEIGHTS.items():
        total += scores.get(obj, 0.5) * weight

    final = total * gasa_penalty

    # Hard-stop: drastic scaffold destruction caps the score regardless of ADMET wins.
    # Without this cap, "phenyl → cyclohexyl" on a kinase inhibitor scaffold (which
    # destroys the aromatic π-stacking interaction) could still rank #1 just because
    # the ADMET model predicted lower CYP/hERG values.
    if scaffold_destroyed:
        final = min(final, 0.30)

    return round(final, 4)


def rank_analogs(
    analogs: List[Dict],
    lead_admet: Dict,
    context_analysis: ContextAnalysis,
    tanimoto_scores: List[float] = None,
    user_context: str = "",
    lead_gasa_hard: float = 0.0,
    lead_smiles: str = ""
) -> List[Dict]:
    """
    Rank all analogs using context-aware multi-endpoint Pareto scoring.

    lead_smiles is required to compute Murcko scaffold preservation. Callers should
    always pass it; the empty-default is for backward compatibility with old call
    sites and will skip the scaffold check (yielding a neutral 0.5 scaffold score).
    """
    if tanimoto_scores is None:
        tanimoto_scores = [0.5] * len(analogs)

    for i, analog in enumerate(analogs):
        tani = tanimoto_scores[i] if i < len(tanimoto_scores) else 0.5
        analog["_lead_gasa_hard"] = lead_gasa_hard
        score = calculate_pareto_score(
            analog, lead_admet, context_analysis, tani, user_context, lead_gasa_hard,
            lead_smiles=lead_smiles,
        )
        analog["pareto_score"] = score

    # Sort by score descending
    analogs.sort(key=lambda a: a["pareto_score"], reverse=True)

    for i, analog in enumerate(analogs):
        analog["pareto_rank"] = i + 1

    disqualified = sum(1 for a in analogs if a["pareto_score"] == 0.0)
    scaffold_capped = sum(1 for a in analogs if a.get("pareto_score", 0) <= 0.30 and a.get("pareto_score", 0) > 0)
    implausible = sum(1 for a in analogs if a.get("_admet_implausible"))
    passing = [a for a in analogs if a["pareto_score"] > 0.0]

    top_score = passing[0]['pareto_score'] if passing else 0.0
    logger.info(
        f"Ranked {len(analogs)} analogs. "
        f"Disqualified: {disqualified}, scaffold-capped (≤0.30): {scaffold_capped}, "
        f"implausible-ADMET-flagged: {implausible}. Top score: {top_score:.4f}"
    )

    return analogs
