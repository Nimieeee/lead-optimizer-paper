import logging
from typing import List, Dict, Tuple, Optional, Set
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold
from .schemas import VisionAgentOutput, SmartsMapping

# Suppress ALL RDKit warnings (C++ and Python level)
RDLogger.logger().setLevel(RDLogger.CRITICAL)
RDLogger.DisableLog('rdApp.*')

logger = logging.getLogger(__name__)

# Comprehensive functional group → SMARTS lookup
# The LLM names groups; Python writes SMARTS.
FUNCTIONAL_GROUP_SMARTS = {
    # Basic groups
    "amidine": "[NX3][CX3]=[NX2]",
    "guanidine": "[NX3][CX3](=[NX2])[NX3]",
    "primary_amine": "[NX3H2][CX4]",
    "secondary_amine": "[NX3H1]([CX4])[CX4]",
    "tertiary_amine": "[NX3]([CX4])([CX4])[CX4]",
    
    # Acid groups
    "carboxylic_acid": "[CX3](=O)[OX2H1]",
    "sulfonic_acid": "[SX4](=O)(=O)[OX2H1]",
    "phosphonic_acid": "[PX4](=O)([OX2H1])[OX2H1]",
    "tetrazole": "c1nn[nH]n1",
    
    # Amides / Carbonyls
    "amide": "[NX3H1][CX3](=O)",
    "sulfonamide": "[NX3][SX4](=O)(=O)",
    "urea": "[NX3H1][CX3](=O)[NX3H1]",
    "carbamate": "[NX3H1][CX3](=O)[OX2]",
    
    # Aromatic rings
    "phenyl": "c1ccccc1",
    "pyridine": "c1ccncc1",
    "pyrimidine": "c1ncncn1",
    "pyrazine": "c1cnccn1",
    "thiophene": "c1ccsc1",
    "furan": "c1ccoc1",
    "imidazole": "c1cnc[nH]1",
    "pyrazole": "c1cc[nH]n1",
    "indole": "c1ccc2c(c1)[nH]cc2",

    # Substituents
    "methoxy": "[CH3][OX2]",
    "ethoxy": "[CH3][CH2][OX2]",
    "hydroxyl": "[OX2H1]",
    "chloro": "[Cl]",
    "bromo": "[Br]",
    "fluoro": "[F]",
    "trifluoromethyl": "[CX4](F)(F)F",
    "trifluoromethoxy": "[OX2][C](F)(F)F",
    "difluoromethoxy": "[OX2][CH](F)F",
    "methyl": "[CH3]",
    "ethyl": "[CH3][CH2]",
    "isopropyl": "[CH](C)C",
    "cyclopropyl": "C1CC1",

    # Special
    "benzyl": "[CH2]c1ccccc1",
    "benzylic_alcohol": "[CH2][OX2H1]",
    "benzyl_alcohol": "[CH2]c1ccccc1[OX2H1]",
    "acetyl": "[CX3](=O)[CH3]",
    "morpholine": "C1COCCN1",
    "piperazine": "C1CNCCN1",
    "piperidine": "C1CCNCC1",
    "cyano": "[CX2]#[NX1]",
    "nitrile": "[CX2]#[NX1]",
    "methylthio": "[SX2][CH3]",
    "methylsulfonyl": "[S](=O)(=O)[CH3]",
    "gem_dimethyl": "[C]([CH3])([CH3])",
    "azetidine": "C1CN1",
    "oxetane": "C1COC1",
    "dihydrobenzofuran": "c1ccc2c(c1)CO2",
    "chromene": "c1ccc2c(c1)OCO2",

    # Audit gap fixes (2026-06-06), medchem groups missing from coverage:
    # Nitro: RDKit canonicalises -NO2 as [N+](=O)[O-]; pattern matches both forms
    "nitro": "[$([NX3](=O)=O),$([N+](=O)[O-])]",
    "primary_nitro": "[CX4][$([NX3](=O)=O),$([N+](=O)[O-])]",
    "nitroso": "[NX2]=O",
    "n_oxide": "[#7+][O-]",
    "azide": "[NX1]=[NX2+]=[N-]",
    "isocyanate": "[NX2]=C=O",
    "isothiocyanate": "[NX2]=C=S",
    "thiocyanate": "[SX2][CX2]#[NX1]",
    "ethynyl": "[CX2]#[CH]",
    "alkyne": "[CX2]#[CX2]",
    "alkene": "[CX3]=[CX3]",
    "vinyl": "[CH2]=[CH]",
    "aziridine": "C1CN1",  # 3-membered N ring (same SMARTS as azetidine, RDKit will match both, downstream uses the wider definition)
    "tert_butyl": "C(C)(C)C",
    "trifluoromethylsulfone": "[S](=O)(=O)C(F)(F)F",
    "aryl_sulfonamide": "c[SX4](=O)(=O)[NX3]",
    "benzofuran": "c1ccc2occc2c1",
    "benzimidazole": "c1nc2ccccc2[nH]1",
    "benzothiazole": "c1nc2ccccc2s1",
    "quinoline": "c1ccc2ncccc2c1",
    "isoquinoline": "c1ccc2cnccc2c1",
    "tertiary_alcohol": "[CX4]([CX4])([CX4])[OX2H1]",
    "carbonyl": "[CX3]=O",
    "ester": "[CX3](=O)[OX2][CX4]",
    "ether": "[OX2]([CX4])[CX4]",
    "thioether": "[SX2]([CX4])[CX4]",
    "sulfoxide": "[SX3](=O)",
    "sulfone": "[SX4](=O)(=O)",
    "phosphate": "[PX4](=O)([OX2])([OX2])",
    "aldehyde": "[CX3H1](=O)",
    "ketone": "[CX3](=O)[CX4]",
    "halide_chloride": "[CX4][Cl]",
    "halide_fluoride": "[CX4][F]",
    "halide_bromide": "[CX4][Br]",
    "ring_aryl_chloride": "c[Cl]",
    "ring_aryl_fluoride": "c[F]",
    "epoxide": "C1CO1",

    # ── Phase 1b (2026-06-09): editable-site coverage fixes ─────────────
    # User audit on the DYRK1A LID showed only 3 editable sites surfaced
    # when the LID had 7+ realistic SAR vectors (aromatic C-H positions,
    # gem-dimethyl per-methyl, hydroxymethyl). These entries surface those
    # sites to the auto-classify path so the Optimization Agent + fallback
    # pulls in the matching SMIRKS (AROM_001-006 for aromatic_h, etc.).
    #
    # aromatic_h: any aromatic carbon with exactly one implicit H, the
    # classic medchem substitution vector. Matches 6+ positions on
    # typical biaryl scaffolds.
    "aromatic_h": "[cH]",
    # hydroxymethyl: -CH2-OH on a NON-aromatic anchor only. The benzylic
    # case is handled by `benzylic_alcohol`, making this overlap-free
    # prevents the Vision Agent from triple-classifying a single Ar-CH2-OH
    # as hydroxyl + benzylic_alcohol + hydroxymethyl (verified 2026-06-09).
    "hydroxymethyl": "[CX4H2;!$([CX4H2]c);!$([CX4H2]a)][OX2H1]",
    # alpha_methyl: a methyl on a tetrahedral carbon (not in a ring) ,
    # exposes the geometric per-methyl decoration sites that gem_dimethyl
    # collapses into one site.
    "alpha_methyl": "[CH3][CX4]",
}

CORE_SCAFFOLD_GROUPS = {
    "phenyl", "pyridine", "pyrimidine", "pyrazine", "thiophene",
    "furan", "imidazole", "pyrazole", "indole", "chromene",
    "dihydrobenzofuran", "benzofuran", "morpholine", "piperazine", "piperidine",
    "azetidine", "oxetane", "tetrazole"
}

def compute_murcko_scaffold(mol: Chem.Mol) -> Tuple[Set[int], str]:
    """
    Compute the Bemis-Murcko scaffold (ring systems + linker atoms).

    Returns:
      scaffold_atoms: set of atom indices IN THE INPUT mol that belong to the scaffold.
      scaffold_smarts: SMARTS pattern of the scaffold (used to enforce preservation
                      via enforce_pharmacophore on downstream analogs).

    Why this matters: SMIRKS-based permutation will happily destroy ring atoms if
    a transformation matches. Adding the scaffold pattern to restricted_smarts
    causes enforce_pharmacophore to reject analogs that lost a scaffold atom ,
    catches the "scaffold methyl misclassified as decoration" failure mode.
    """
    if mol is None:
        return set(), ""
    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        if scaffold is None or scaffold.GetNumAtoms() == 0:
            return set(), ""
        # Map scaffold atoms back to indices in the original mol via substructure match
        scaffold_smarts = Chem.MolToSmarts(scaffold)
        scaffold_pattern = Chem.MolFromSmarts(scaffold_smarts)
        if scaffold_pattern is None:
            return set(), ""
        matches = mol.GetSubstructMatches(scaffold_pattern)
        scaffold_atoms = set()
        for match in matches:
            scaffold_atoms.update(match)
        return scaffold_atoms, scaffold_smarts
    except Exception as e:
        logger.warning(f"Murcko scaffold computation failed: {e}")
        return set(), ""


def _position_hint_from_2d(mol, atom_indices: Tuple[int, ...]) -> str:
    """Return a chemist-friendly position hint ('left', 'right', 'central',
    'top', 'bottom') based on the 2D centroid of the match's atoms relative
    to the whole molecule's bounding box.

    This gives the Vision Agent a stable anchor for disambiguating multiple
    matches of the same SMARTS (two phenyl rings, three methyls, etc.) that
    correlates with what a chemist sees in the LID, without forcing the
    model to guess atom indices it can't see.
    """
    try:
        if mol.GetNumConformers() == 0:
            AllChem.Compute2DCoords(mol)
        conf = mol.GetConformer()
        all_pts = [conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())]
        min_x = min(p.x for p in all_pts)
        max_x = max(p.x for p in all_pts)
        min_y = min(p.y for p in all_pts)
        max_y = max(p.y for p in all_pts)
        span_x = max(max_x - min_x, 0.001)
        span_y = max(max_y - min_y, 0.001)

        pts = [conf.GetAtomPosition(i) for i in atom_indices]
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        # Normalise centroid to [0, 1] across the bounding box
        nx = (cx - min_x) / span_x
        ny = (cy - min_y) / span_y

        if nx < 0.33:
            h = "left"
        elif nx > 0.67:
            h = "right"
        else:
            h = "central"
        if ny > 0.67:
            return f"{h}-top"
        if ny < 0.33:
            return f"{h}-bottom"
        return h
    except Exception:
        return "unknown"


def _label_instances(
    name: str,
    matches: List[Tuple[int, ...]],
    mol,
) -> List[Tuple[str, Tuple[int, ...], str]]:
    """Build (label, atom_indices, position_hint) for each match of a group name.

    Single match → label is the group name (no suffix).
    Multiple matches → labels suffixed with position hint, then index for
    ties. Examples: phenyl_left, phenyl_right; methyl_left, methyl_central,
    methyl_right; aromatic_h_1, aromatic_h_2, ...
    """
    if len(matches) == 1:
        return [(name, matches[0], _position_hint_from_2d(mol, matches[0]))]

    # Multiple matches, compute position hints and dedup by appending index
    hints = [_position_hint_from_2d(mol, m) for m in matches]
    seen: Dict[str, int] = {}
    labels = []
    for i, (m, h) in enumerate(zip(matches, hints)):
        candidate = f"{name}_{h}" if h != "unknown" else f"{name}_{i+1}"
        if candidate in seen:
            seen[candidate] += 1
            candidate = f"{candidate}_{seen[candidate]}"
        else:
            seen[candidate] = 1
        labels.append((candidate, m, h))
    return labels


def pre_scan_molecule(lead_smiles: str) -> dict:
    """
    Deterministic substructure detection using RDKit.

    Per-instance labeling (2026-06-09): every match of every functional
    group gets a unique label ("phenyl_left", "phenyl_right") so the Vision
    Agent can classify each instance separately. This solves the bug where
    a molecule with two phenyl rings had ONE classified as restricted (pi-
    stack) and the OTHER as target, but the underlying SMARTS matched both,
    so both got frozen.

    Returns:
      all: list of unique group names (each appears once even if multi-match)
      labeled: list of (label, name, atom_indices, position_hint), the
               authoritative per-instance enumeration. Use these as the
               unit of classification.
      core_rings: subset of `all` that are scaffold-forming heterocycles
      peripheral: subset of `all` NOT in CORE_SCAFFOLD_GROUPS
      scaffold_atoms: set of RDKit atom indices in the Bemis-Murcko scaffold
      scaffold_smarts: SMARTS of the Murcko scaffold
      groups_with_indices: legacy [(name, atom_indices)], preserved for
                          backwards-compat with older callers
    """
    mol = Chem.MolFromSmiles(lead_smiles)
    if mol is None:
        raise ValueError(f"Invalid lead SMILES: {lead_smiles}")

    # Lazy 2D coords for position hints
    try:
        if mol.GetNumConformers() == 0:
            AllChem.Compute2DCoords(mol)
    except Exception:
        pass

    detected = []
    labeled: List[Dict] = []
    groups_with_indices: List[Tuple[str, Tuple[int, ...]]] = []
    for name, smarts in FUNCTIONAL_GROUP_SMARTS.items():
        pattern = Chem.MolFromSmarts(smarts)
        if not pattern:
            continue
        matches = mol.GetSubstructMatches(pattern)
        if matches:
            detected.append(name)
            for label, atom_idx, hint in _label_instances(name, list(matches), mol):
                labeled.append({
                    "label": label,
                    "name": name,
                    "atom_indices": list(atom_idx),
                    "position_hint": hint,
                })
                groups_with_indices.append((name, atom_idx))

    scaffold_atoms, scaffold_smarts = compute_murcko_scaffold(mol)

    return {
        'all': detected,
        'labeled': labeled,
        'core_rings': [g for g in detected if g in CORE_SCAFFOLD_GROUPS],
        'peripheral': [g for g in detected if g not in CORE_SCAFFOLD_GROUPS],
        'scaffold_atoms': scaffold_atoms,
        'scaffold_smarts': scaffold_smarts,
        'groups_with_indices': groups_with_indices,
    }

def _resolve_label(label_or_name: str, labeled_instances: List[Dict]) -> Tuple[str, Optional[List[int]]]:
    """Map a Vision Agent label back to (base_name, atom_indices).

    Three cases:
      1. Exact label match (e.g. "phenyl_left") → return (base_name, atoms)
      2. Bare name match when only one instance exists → return (name, atoms)
      3. Bare name when multiple instances exist → return (name, None)
         and let the caller treat all matches as the unit (no per-instance
         disambiguation possible).
    """
    if not labeled_instances:
        return label_or_name, None
    norm = label_or_name.lower().replace(" ", "_")
    # Try exact label match first
    for inst in labeled_instances:
        if inst.get("label", "").lower() == norm:
            return inst.get("name", norm), list(inst.get("atom_indices") or [])
    # Try bare-name match
    matches_for_name = [inst for inst in labeled_instances if inst.get("name", "").lower() == norm]
    if len(matches_for_name) == 1:
        # Unambiguous
        return matches_for_name[0].get("name", norm), list(matches_for_name[0].get("atom_indices") or [])
    if len(matches_for_name) > 1:
        # Ambiguous, multiple instances under the same bare name
        return matches_for_name[0].get("name", norm), None
    # Unknown
    return norm, None


def _atom_set_smarts(mol, atom_indices: List[int]) -> str:
    """Build a SMARTS pattern that matches the EXACT atoms listed (by element
    + connectivity around the seed atoms). Used to lock a specific instance
    of a group (e.g. only the left phenyl ring) without affecting other
    instances of the same chemistry."""
    if not atom_indices:
        return ""
    try:
        # MolFragmentToSmarts produces a SMARTS for the specific atom set
        smarts = Chem.MolFragmentToSmarts(
            mol,
            atomsToUse=list(atom_indices),
            isomericSmarts=False,
        )
        # Validate parses back
        if smarts and Chem.MolFromSmarts(smarts) is not None:
            return smarts
    except Exception:
        pass
    return ""


def build_smarts_from_groups(
    lead_smiles: str,
    vision_output: VisionAgentOutput,
    detected_groups: List[str] = None,
    scaffold_atoms: Optional[Set[int]] = None,
    scaffold_smarts: str = "",
    labeled_instances: Optional[List[Dict]] = None,
) -> SmartsMapping:
    """
    Convert Vision Agent's group classifications into validated SMARTS.

    Architecture (Approach A + soft scaffold gate, post-2026-06-06):
    - Group DETECTION is handled by pre_scan_molecule() (RDKit, deterministic)
    - This function VALIDATES Vision Agent groups against the detection set
      (hallucinated group names are dropped)
    - THREE input categories from the Vision Agent:
        restricted (binding-essential) → restricted_parts
        structural_core (chemotype-defining, no protein contact) → restricted_parts
        target (editable) → target_parts
    - Unclaimed detected groups DEFAULT TO TARGET. The previous "auto-restrict
      anything scaffold-embedded" rule was over-aggressive and froze
      legitimate SAR vectors (alpha-methyls on scaffold rings). Now we let
      the Vision Agent's STRUCTURAL_CORE category own that call.
    - SOFT Murcko scaffold gate: scaffold_smarts is NOT appended to
      restricted_smarts. Instead, enforce_pharmacophore checks ring-topology
      preservation (count + aromaticity) rather than exact SMARTS match ,
      this allows methyl→ethyl on a scaffold carbon while still rejecting
      ring-system destruction.
    """
    mol = Chem.MolFromSmiles(lead_smiles)
    if mol is None:
        raise ValueError(f"Invalid lead SMILES: {lead_smiles}")

    group_to_smarts = {}
    restricted_parts = []
    target_parts = []
    detected_set = set(detected_groups) if detected_groups else set()
    # Per-instance atom-index tracking for the Layer 3 / 4 disambiguation:
    # we record which atom set each restricted entry "claims" so that
    # downstream code (and the Layer 4 safety default) can detect when
    # the same bare group name appears in BOTH restricted and target.
    restricted_atom_sets: List[Tuple[str, List[int]]] = []  # (base_name, atom_indices)

    # Merge Murcko atoms with any vision-flagged scaffold atoms
    all_scaffold_atoms: Set[int] = set(scaffold_atoms or set())
    if vision_output.scaffold_atoms:
        all_scaffold_atoms.update(vision_output.scaffold_atoms)

    # Pre-compute: which BASE names did the Vision Agent put in TARGET?
    # Layer 4 safety default: when the model puts the same base name in BOTH
    # restricted and target (e.g. "phenyl" both ways without distinguishing
    # instances via labels), trust the chemist's "everything else is editable"
    # policy, drop the restricted entry and route to target. The
    # ring-topology safety net in enforce_pharmacophore catches catastrophic
    # cases.
    target_base_names: Set[str] = set()
    for tg in vision_output.target_groups:
        _bn, _ = _resolve_label((tg.group_name or "").strip(), labeled_instances or [])
        if _bn:
            target_base_names.add(_bn.lower())

    restricted_names = set()
    target_names_list = []  # Ordered list aligned with target_parts

    logger.debug(f"DEBUG: SMARTS Builder - Validating {len(vision_output.restricted_groups)} restricted groups against {len(detected_groups or [])} RDKit-detected groups...")
    for i, group in enumerate(vision_output.restricted_groups):
        raw_label = (group.group_name or "").strip()
        base_name, atom_indices = _resolve_label(raw_label, labeled_instances or [])
        norm_base = base_name.lower().replace(" ", "_")
        logger.debug(f"DEBUG:   [{i+1}/{len(vision_output.restricted_groups)}] Restricted: label={raw_label!r} → base={norm_base!r} atoms={atom_indices}")
        if norm_base not in FUNCTIONAL_GROUP_SMARTS:
            logger.warning(f"⚠️ Skipping unknown restricted group: {norm_base}")
            continue
        if detected_set and norm_base not in detected_set:
            logger.warning(f"⚠️ Vision Agent hallucinated '{norm_base}', not found in molecule by RDKit. Skipping.")
            continue
        # Layer 4 SAFETY DEFAULT: same base name in both lists with no
        # per-instance distinction → route to TARGET.
        ambiguous_dual_classification = (
            norm_base in target_base_names and
            atom_indices is None and
            # Multiple matches of this name exist in the molecule (so the
            # caller could in principle distinguish them via labels)
            sum(1 for inst in (labeled_instances or []) if inst.get("name", "").lower() == norm_base) > 1
        )
        if ambiguous_dual_classification:
            logger.warning(
                f"⚠️ '{norm_base}' classified as BOTH restricted and target without per-instance labels, "
                f"safety default: routing to TARGET (chemist policy: 'everything else editable'). "
                f"If the contact is real, override in the human-review panel."
            )
            continue

        smarts = FUNCTIONAL_GROUP_SMARTS[norm_base]
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None:
            logger.warning(f"⚠️ Invalid SMARTS for {norm_base}: {smarts}")
            continue
        if not mol.HasSubstructMatch(pattern):
            if not mol.HasSubstructMatch(Chem.MolFromSmarts(smarts.lower())):
                logger.warning(f"⚠️ Group '{norm_base}' ({smarts}) not found in lead molecule. Skipping.")
                continue

        # Per-instance SMARTS when labels gave us specific atom indices.
        # Falls back to the generic SMARTS when the label was ambiguous or
        # absent, preserving backward compatibility with callers that
        # don't yet pass labeled_instances.
        if atom_indices:
            instance_smarts = _atom_set_smarts(mol, atom_indices)
            if instance_smarts:
                if instance_smarts not in restricted_parts:
                    restricted_parts.append(instance_smarts)
                    restricted_atom_sets.append((norm_base, list(atom_indices)))
                group_to_smarts[raw_label or norm_base] = instance_smarts
                restricted_names.add(raw_label or norm_base)
                logger.debug(f"DEBUG:     Per-instance SMARTS for {raw_label}: {instance_smarts}")
                continue
        # Fallback: generic SMARTS for the group name
        group_to_smarts[norm_base] = smarts
        restricted_parts.append(smarts)
        restricted_atom_sets.append((norm_base, []))
        restricted_names.add(norm_base)
    
    # POLICY (2026-06-09): legacy structural_core_groups field is treated as
    # TARGET, not restricted. The chemist's correction: only groups making
    # visible protein contacts in the LID belong in restricted. Scaffold
    # atoms, gem-dimethyls, aromatic_h etc. are legitimate SAR vectors and
    # must be editable. The soft Murcko topology gate in enforce_pharmacophore
    # is the safety net against catastrophic scaffold destruction.
    structural_core_names = getattr(vision_output, "structural_core_groups", []) or []
    if structural_core_names:
        logger.debug(f"DEBUG: SMARTS Builder - Routing {len(structural_core_names)} structural_core entries to TARGET (per 2026-06-09 policy)")
    for i, group in enumerate(structural_core_names):
        name = group.group_name.lower().replace(" ", "_")
        if name not in FUNCTIONAL_GROUP_SMARTS:
            continue
        if detected_set and name not in detected_set:
            continue
        smarts = FUNCTIONAL_GROUP_SMARTS[name]
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None or not mol.HasSubstructMatch(pattern):
            continue
        # Route to target_parts (editable), not restricted_parts
        if smarts not in target_parts and name not in target_names_list:
            target_parts.append(smarts)
            target_names_list.append(name)
            group_to_smarts[name] = smarts

    logger.debug(f"DEBUG: SMARTS Builder - Validating {len(vision_output.target_groups)} target groups...")
    for i, group in enumerate(vision_output.target_groups):
        raw_label = (group.group_name or "").strip()
        base_name, atom_indices = _resolve_label(raw_label, labeled_instances or [])
        norm_base = base_name.lower().replace(" ", "_")
        logger.debug(f"DEBUG:   [{i+1}/{len(vision_output.target_groups)}] Target: label={raw_label!r} → base={norm_base!r} atoms={atom_indices}")
        if norm_base not in FUNCTIONAL_GROUP_SMARTS:
            logger.warning(f"⚠️ Skipping unknown target group: {norm_base}")
            continue
        if detected_set and norm_base not in detected_set:
            logger.warning(f"⚠️ Vision Agent hallucinated target '{norm_base}'. Skipping.")
            continue

        # Per-instance SMARTS when atom indices are known
        if atom_indices:
            instance_smarts = _atom_set_smarts(mol, atom_indices)
            if instance_smarts and instance_smarts not in target_parts:
                target_parts.append(instance_smarts)
                target_names_list.append(raw_label or norm_base)
                group_to_smarts[raw_label or norm_base] = instance_smarts
                logger.debug(f"DEBUG:     Per-instance target SMARTS for {raw_label}: {instance_smarts}")
                continue
        # Fallback: generic SMARTS
        smarts = FUNCTIONAL_GROUP_SMARTS[norm_base]
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None or not mol.HasSubstructMatch(pattern):
            continue
        if smarts not in target_parts:
            target_parts.append(smarts)
            target_names_list.append(norm_base)
            group_to_smarts[norm_base] = smarts

    # Auto-classify unclaimed detected groups. POLICY CHANGE (2026-06-06):
    # Unclassified peripheral groups DEFAULT TO TARGET unless they are a
    # named core-ring system (pyridine, indole, etc.). The previous
    # "auto-restrict anything whose atoms are in the Murcko scaffold" rule
    # was over-aggressive and froze legitimate SAR vectors (alpha-methyl,
    # ring-decorating gem-dimethyl). The Vision Agent's STRUCTURAL_CORE
    # category now owns that call, if the model didn't flag a group as
    # structural_core, we trust it's editable.
    if detected_groups:
        logger.debug(f"DEBUG: SMARTS Builder - Auto-classifying {len(detected_groups)} unclaimed groups...")
        for name in detected_groups:
            if name in restricted_names or name in target_names_list:
                continue
            smarts = FUNCTIONAL_GROUP_SMARTS.get(name)
            if not smarts:
                continue
            pattern = Chem.MolFromSmarts(smarts)
            if not pattern or not mol.HasSubstructMatch(pattern):
                continue

            if name in CORE_SCAFFOLD_GROUPS:
                # Named heterocycles defining the scaffold (pyridine, indole, etc.)
                # stay restricted even if vision agent missed them, these are
                # unambiguously chemotype-defining.
                if smarts not in restricted_parts:
                    logger.debug(f"DEBUG:   AUTO-RESTRICTED (core ring): {name}")
                    restricted_parts.append(smarts)
                    restricted_names.add(name)
                    group_to_smarts[name] = smarts
            else:
                # Default: peripheral → editable. The soft scaffold gate
                # (enforce_scaffold_topology, applied in enforce_pharmacophore)
                # catches catastrophic ring destruction at the analog-validation
                # stage without freezing every scaffold-adjacent decoration here.
                if smarts not in target_parts:
                    logger.debug(f"DEBUG:   AUTO-TARGET (peripheral, default): {name}")
                    target_parts.append(smarts)
                    target_names_list.append(name)
                    group_to_smarts[name] = smarts

    # NOTE: Murcko scaffold SMARTS is NO LONGER appended to restricted_parts.
    # The soft topology check in enforce_pharmacophore (ring count + aromaticity
    # preservation) replaces the exact-SMARTS hard gate. This allows
    # legitimate SAR modifications (e.g. methyl → ethyl on a scaffold carbon)
    # while still rejecting ring-system destruction.

    restricted_combined = ".".join(restricted_parts) if restricted_parts else ""

    logger.debug(f"DEBUG: SMARTS Builder - Final: {len(restricted_parts)} restricted, {len(target_parts)} target")
    return SmartsMapping(
        restricted_smarts=restricted_combined,
        target_smarts=target_parts,
        group_to_smarts=group_to_smarts,
        group_names=target_names_list
    )

def validate_smirks(smirks: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a SMIRKS reaction string.
    """
    try:
        rxn = AllChem.ReactionFromSmarts(smirks)
        if rxn is None:
            return False, "ReactionFromSmarts returned None"
        if rxn.GetNumReactantTemplates() == 0:
            return False, "No reactant templates"
        if rxn.GetNumProductTemplates() == 0:
            return False, "No product templates"
        return True, None
    except Exception as e:
        return False, f"SMIRKS parse error: {str(e)}"

def _sanitize_product(product) -> bool:
    """
    Attempt to sanitize a product molecule with multiple strategies.
    Returns True if successfully sanitized, False otherwise.
    """
    try:
        Chem.SanitizeMol(product)
        return True
    except Exception:
        pass

    try:
        Chem.SanitizeMol(product, Chem.SANITIZE_ALL ^ Chem.SANITIZE_SETAROMATICITY)
        Chem.Kekulize(product, clearAromaticFlags=True)
        return True
    except Exception:
        pass

    try:
        Chem.SanitizeMol(product, Chem.SANITIZE_ALL ^ Chem.SANITIZE_KEKULIZE ^ Chem.SANITIZE_SETAROMATICITY)
        return True
    except Exception:
        pass

    return False


def execute_smirks_substitution(
    lead_smiles: str,
    smirks: str
) -> List[str]:
    """
    Execute a SMIRKS-based molecular transformation.
    """
    try:
        mol = Chem.MolFromSmiles(lead_smiles)
        if mol is None:
            logger.error(f"Invalid lead SMILES: {lead_smiles}")
            return []
        
        rxn = AllChem.ReactionFromSmarts(smirks)
        if rxn is None:
            logger.error(f"Invalid SMIRKS: {smirks}")
            return []
        
        products = rxn.RunReactants((mol,))
        valid_smiles = []
        seen = set()
        
        for product_set in products:
            for product in product_set:
                try:
                    if _sanitize_product(product):
                        smi = Chem.MolToSmiles(product, canonical=True)
                        if smi not in seen and smi != lead_smiles:
                            seen.add(smi)
                            valid_smiles.append(smi)
                except Exception:
                    continue
        
        return valid_smiles
        
    except Exception as e:
        logger.error(f"SMIRKS execution error: {e}")
        return []

def _ring_topology_profile(mol: Chem.Mol) -> Tuple[int, int, int]:
    """Cheap topology fingerprint used by the soft scaffold gate.

    Returns (total_rings, aromatic_rings, fused_atoms). Two molecules with
    the same triple have isomorphic ring systems at the topology level ,
    they may differ in decoration but the chemotype identity is preserved.
    """
    if mol is None:
        return (0, 0, 0)
    try:
        ring_info = mol.GetRingInfo()
        atom_rings = ring_info.AtomRings()
        total = len(atom_rings)
        aromatic = sum(
            1 for ring in atom_rings
            if all(mol.GetAtomWithIdx(a).GetIsAromatic() for a in ring)
        )
        fused_atoms = sum(
            1 for atom in mol.GetAtoms() if ring_info.NumAtomRings(atom.GetIdx()) > 1
        )
        return (total, aromatic, fused_atoms)
    except Exception:
        return (0, 0, 0)


def enforce_pharmacophore(
    new_smiles: str,
    restricted_smarts_parts: List[str],
    lead_smiles: Optional[str] = None,
) -> bool:
    """Verify the analog preserves restricted pharmacophore + scaffold topology.

    Two checks:
      1. EVERY restricted SMARTS must still match the analog (hard contract ,
         these are binding-essential groups that SMIRKS must not destroy).
      2. If `lead_smiles` is provided, the analog's ring topology profile
         (total rings, aromatic rings, fused atoms) must match the lead's.
         This is the SOFT scaffold gate, it allows methyl→ethyl on a
         scaffold carbon (same ring topology) but rejects ring-system
         destruction (different topology).

    The lead_smiles parameter is optional for backwards compatibility with
    callers that don't yet pass it. When omitted, only check #1 runs.
    """
    try:
        mol = Chem.MolFromSmiles(new_smiles)
        if mol is None:
            return False
        # Check 1: restricted SMARTS preservation (hard).
        for smarts in restricted_smarts_parts:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern is None:
                continue
            if not mol.HasSubstructMatch(pattern):
                return False
        # Check 2: soft scaffold topology (only if lead provided).
        if lead_smiles:
            lead_mol = Chem.MolFromSmiles(lead_smiles)
            if lead_mol is not None:
                lead_profile = _ring_topology_profile(lead_mol)
                analog_profile = _ring_topology_profile(mol)
                if lead_profile != analog_profile:
                    return False
        return True
    except Exception:
        return False

def calculate_sa_score(smiles: str) -> Optional[float]:
    """
    Calculate Synthetic Accessibility score.
    Requires sascorer from RDContrib.
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        from rdkit.Chem import RDConfig
        import os, sys
        sa_path = os.path.join(RDConfig.RDContribDir, 'SA_Score')
        if sa_path not in sys.path:
            sys.path.insert(0, sa_path)
        
        try:
            import sascorer
            return sascorer.calculateScore(mol)
        except ImportError:
            logger.warning("sascorer not found, using placeholder SA score")
            return 5.0 # Neutral placeholder
            
    except Exception as e:
        logger.error(f"SA score calculation failed: {e}")
        return None

# Conservative SMIRKS categories for secondary target modifications
CONSERVATIVE_CATEGORIES = {
    "aromatic_substitutions",
    "bioisosteric_replacements",
    "halogen_substitutions",
    "heteroatom_replacements",
    "polarity_adjustments",
    "ring_expansion",
    "ring_contraction",
    "ester_modifications",
    "carboxylic_acid_replacements",
    "amide_modifications"
}

def is_conservative_smirks(smirks_id: str) -> bool:
    """
    Check if a SMIRKS transformation is conservative enough for secondary targets.
    Conservative modifications preserve the overall scaffold while making 
    subtle electronic/steric adjustments.
    """
    from .smirks_library import SMIRKS_LIBRARY
    entry = SMIRKS_LIBRARY.get(smirks_id)
    if not entry:
        return False
    return entry.category in CONSERVATIVE_CATEGORIES
