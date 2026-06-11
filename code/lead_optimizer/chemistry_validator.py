"""
Chemistry-validity tables for Vision Agent output.

Every (group_name, interaction_type) tuple emitted by the Vision Agent
is checked against these tables before the output reaches the user-review
UI or downstream stages. Tuples that are physically impossible are
dropped, `methyl` can never be an h_bond_donor, `methoxy` can never be
a donor (the oxygen has no proton), etc.

This is a structural guard: even a perfect vision model occasionally
hallucinates interaction types under JSON mode, and the user-facing
review panel should never display a chemically impossible classification.

Mirrors the Vision Agent prompt's Rule 6, keep the two in sync.
"""
from typing import Set


H_BOND_DONORS: Set[str] = {
    # Groups with a polar O-H, N-H, or S-H proton
    "hydroxyl",
    "primary_amine",
    "secondary_amine",
    # Tertiary amine has no N-H, kept here only for amines like piperidine
    # where the secondary NH of the ring counts; downstream check by name.
    "amide",
    "urea",
    "carbamate",
    "sulfonamide",
    "carboxylic_acid",
    "imidazole",
    "indole",
    "pyrazole",
    "guanidine",
    "amidine",
    "tetrazole",
    "benzylic_alcohol",
    "benzyl_alcohol",
    "piperidine",       # secondary NH in ring
    "piperazine",       # two secondary NHs
    "morpholine",       # secondary NH in ring
    "azetidine",        # NH in strained ring
}

H_BOND_ACCEPTORS: Set[str] = {
    # Groups with a lone-pair-bearing O, N, or S accessible to H-bond
    "methoxy",
    "ethoxy",
    "hydroxyl",
    "trifluoromethoxy",
    "difluoromethoxy",
    "amide",
    "urea",
    "carbamate",
    "carboxylic_acid",
    "sulfonamide",
    "pyridine",
    "pyrimidine",
    "pyrazine",
    "imidazole",
    "pyrazole",
    "thiophene",        # weak, but reported in pharmacophore analysis
    "furan",
    "morpholine",
    "piperazine",
    "piperidine",
    "azetidine",
    "oxetane",
    "cyano",
    "nitrile",
    "acetyl",
    "guanidine",
    "amidine",
    "tetrazole",
    "methylsulfonyl",
    "methylthio",
}

PI_STACK_GROUPS: Set[str] = {
    # Aromatic (or sufficiently planar conjugated) ring systems
    "phenyl",
    "pyridine",
    "pyrimidine",
    "pyrazine",
    "thiophene",
    "furan",
    "imidazole",
    "pyrazole",
    "indole",
    "chromene",
    "dihydrobenzofuran",
}

HYDROPHOBIC_GROUPS: Set[str] = {
    # Non-polar alkyl / aromatic carbon
    "methyl",
    "ethyl",
    "isopropyl",
    "cyclopropyl",
    "trifluoromethyl",
    "phenyl",
    "benzyl",
    "gem_dimethyl",
}

SALT_BRIDGE_GROUPS: Set[str] = {
    # Anionic at physiological pH
    "carboxylic_acid",
    "sulfonic_acid",
    "phosphonic_acid",
    "tetrazole",
    # Cationic at physiological pH
    "primary_amine",
    "secondary_amine",
    "tertiary_amine",
    "guanidine",
    "amidine",
    "imidazole",
}

CATION_PI_GROUPS: Set[str] = {
    # Aromatic acceptors of cation-pi
    "phenyl",
    "pyridine",
    "pyrimidine",
    "indole",
    # Cationic donors of cation-pi
    "primary_amine",
    "tertiary_amine",
    "guanidine",
    "amidine",
}

INTERACTION_ALLOWED = {
    "h_bond_donor": H_BOND_DONORS,
    "h_bond_acceptor": H_BOND_ACCEPTORS,
    "pi_stack": PI_STACK_GROUPS,
    "hydrophobic": HYDROPHOBIC_GROUPS,
    "salt_bridge": SALT_BRIDGE_GROUPS,
    "cation_pi": CATION_PI_GROUPS,
}


_NOISE_SUFFIXES = ("_group", "_groups", "_function", "_substituent", "_moiety", "_fragment")


def normalize_group_name(raw: str) -> str:
    """Lowercase + underscore + drop noise suffixes.

    Handles: 'Methyl', 'methyl', 'methyl group', 'Methyl-Group', 'Methyl moiety'
    all → 'methyl'. Models sometimes append qualifiers that the allowlist
    doesn't carry, so we strip them.
    """
    if not raw:
        return ""
    n = raw.strip().lower().replace(" ", "_").replace("-", "_")
    # Collapse double underscores caused by multiple spaces / dashes
    while "__" in n:
        n = n.replace("__", "_")
    for suffix in _NOISE_SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)]
            break
    return n


def is_valid_interaction(group_name: str, interaction_type: str) -> bool:
    """Return True if the (group, interaction) pair is chemically possible.

    Unknown group_name → False (we don't recognise it, so refuse to validate).
    Unknown interaction_type → False (out of allowed enum).
    """
    if not group_name or not interaction_type:
        return False
    allowed = INTERACTION_ALLOWED.get(interaction_type)
    if allowed is None:
        return False
    return normalize_group_name(group_name) in allowed
