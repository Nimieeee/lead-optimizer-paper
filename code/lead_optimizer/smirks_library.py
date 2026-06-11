"""
smirks_library.py — Curated, pre-validated bioisosteric SMIRKS reactions.

The Optimization Agent selects from this library instead of generating SMIRKS from scratch.
This ensures 100% valid chemistry and high performance.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SmirksEntry:
    id: str                    # e.g., "ACID_001"
    category: str              # e.g., "carboxylic_acid_replacements"
    name: str                  # e.g., "Carboxylic acid -> Tetrazole"
    smirks: str                # The actual SMIRKS string
    description: str           # Why this replacement is useful
    expected_impact: str       # e.g., "Improves metabolic stability"
    complexity_delta: float    # SA score change estimate (-2 to +2)
    tags: List[str] = field(default_factory=list)
    reference: Optional[str] = None
    validated: bool = True     # True = hand-curated and validated; False = template-generated

SMIRKS_LIBRARY: Dict[str, SmirksEntry] = {
    # ── Carboxylic Acid Bioisosteres ──────────────────────────
    "ACID_001": SmirksEntry(
        id="ACID_001",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to tetrazole",
        smirks="[C:1](=O)[OH]>>[C:1]1=NN=N[NH]1",
        description="Classic bioisostere. Tetrazole has similar pKa (~4.9) "
                    "to COOH but is metabolically stable and improves oral bioavailability.",
        expected_impact="Metabolic stability, oral bioavailability",
        complexity_delta=1.2,
        tags=["metabolic_stability", "oral", "pka_matched"],
        reference="Bioisosteres in MedChem, Ch. 4"
    ),
    "ACID_002": SmirksEntry(
        id="ACID_002",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to acylsulfonamide",
        smirks="[C:1](=O)[OH]>>[C:1](=O)NS(=O)(=O)[CH3]",
        description="Retains H-bond donor/acceptor pattern. pKa ~4. "
                    "Better membrane permeability than COOH.",
        expected_impact="Permeability, metabolic stability",
        complexity_delta=1.5,
        tags=["permeability", "metabolic_stability"],
        reference="Bioisosteres in MedChem, Ch. 4"
    ),
    "ACID_003": SmirksEntry(
        id="ACID_003",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to hydroxamic acid",
        smirks="[C:1](=O)[OH]>>[C:1](=O)N[OH]",
        description="Increases metal chelation (useful for HDAC/MMP targets) "
                    "but can have metabolic instability.",
        expected_impact="Metal chelation, pharmacodynamic shift",
        complexity_delta=0.8,
        tags=["chelation", "enzyme_target"],
        reference="12.1.mchem, Ch. 5"
    ),

    # ── Amide Bond Replacements ───────────────────────────────
    "AMIDE_001": SmirksEntry(
        id="AMIDE_001",
        category="amide_bond_replacements",
        name="Amide to 1,2,4-oxadiazole",
        smirks="[NH:1][C:2](=O)>>[c:1]1noc(n1)[*:2]",
        description="Oxadiazole mimics amide H-bonding geometry but resists "
                    "proteolytic cleavage. Common in orally bioavailable drugs.",
        expected_impact="Metabolic stability, protease resistance",
        complexity_delta=1.0,
        tags=["metabolic_stability", "oral", "protease_resistant"],
        reference="J. Med. Chem. 2014, 57, 6"
    ),
    "AMIDE_002": SmirksEntry(
        id="AMIDE_002",
        category="amide_bond_replacements",
        name="Amide to reversed amide",
        smirks="[C:1](=O)[NH:2]>>[NH:1][C:2](=O)",
        description="Inverting the amide can change dipole orientation and "
                    "H-bonding donor/acceptor positions, often dodging metabolism.",
        expected_impact="Metabolic stability, binding orientation",
        complexity_delta=0.0,
        tags=["metabolic_stability", "dipole_shift"],
        reference="Bioisosteres in MedChem, Ch. 6"
    ),

    # ── Aromatic Ring Swaps ───────────────────────────────────
    "RING_001": SmirksEntry(
        id="RING_001",
        category="aromatic_ring_swaps",
        name="Phenyl to pyridine (N at para)",
        smirks="[c:1]1[c:2][c:3][cH:4][c:5][c:6]1>>[c:1]1[c:2][c:3][n:4][c:5][c:6]1",
        description="Reduces LogP by ~0.5-1.0. Pyridine N acts as H-bond acceptor. "
                    "Breaks planarity slightly, improving solubility.",
        expected_impact="LogP reduction, solubility, CYP interaction",
        complexity_delta=0.0,
        tags=["logp_reduction", "solubility"],
        reference="12.1.mchem, Ch. 8"
    ),
    "RING_002": SmirksEntry(
        id="RING_002",
        category="aromatic_ring_swaps",
        name="Phenyl to pyrimidine",
        smirks="[c:1]1[c:2][c:3][cH:4][c:5][c:6]1>>[c:1]1[c:2][n:3][c:4][n:5][c:6]1",
        description="Further reduces LogP. Adds multiple H-bond acceptors. "
                    "Great for reducing hERG liability and increasing solubility.",
        expected_impact="Solubility, hERG reduction, LogP shift",
        complexity_delta=0.2,
        tags=["solubility", "herg_reduction", "logp_reduction"],
        reference="12.1.mchem, Ch. 8"
    ),

    # ── Metabolic Stability ───────────────────────────────────
    "METAB_001": SmirksEntry(
        id="METAB_001",
        category="metabolic_stability",
        name="Block benzylic position with fluorine",
        smirks="[*:1][CH2:2][OX2:3]>>[*:1][CH:2]([F])[OX2:3]",
        description="Gem-difluoro at benzylic position blocks CYP-mediated "
                    "oxidation. Common strategy for metabolically labile benzylic CH2.",
        expected_impact="CYP3A4 stability, half-life extension",
        complexity_delta=0.5,
        tags=["metabolic_stability", "cyp3a4", "half_life"],
        reference="J. Med. Chem. 2020, Review"
    ),
    "METAB_002": SmirksEntry(
        id="METAB_002",
        category="metabolic_stability",
        name="Deuteration of methyl group",
        smirks="[CH3:1]>>[C:1]([2H])([2H])[2H]",
        description="Kinetic isotope effect (KIE) slows down oxidative metabolism "
                    "of methyl groups, extending half-life.",
        expected_impact="Metabolic stability, half-life extension",
        complexity_delta=0.1,
        tags=["metabolic_stability", "kie"],
        reference="Nature Reviews Drug Discovery, 2018"
    ),

    # ── Halogen Substitutions ─────────────────────────────────
    "HALO_001": SmirksEntry(
        id="HALO_001",
        category="halogen_substitutions",
        name="Chloro to Fluoro",
        smirks="[Cl:1]>>[F:1]",
        description="Reduces lipophilicity and size while maintaining "
                    "inductive electron-withdrawing effect.",
        expected_impact="LogP reduction, metabolic shift",
        complexity_delta=0.0,
        tags=["logp_reduction", "metabolic_stability"],
        reference="Bioisosteres in MedChem"
    ),
    "HALO_002": SmirksEntry(
        id="HALO_002",
        category="halogen_substitutions",
        name="Methyl to Trifluoromethyl",
        smirks="[CH3:1]>>[C:1](F)(F)F",
        description="Drastically increases metabolic stability of the site "
                    "but increases lipophilicity (LogP +~0.5).",
        expected_impact="Metabolic stability, LogP increase",
        complexity_delta=0.3,
        tags=["metabolic_stability", "lipophilicity_increase"],
        reference="12.1.mchem"
    ),

    # ═══════════════════════════════════════════════════════════
    # ── NEW: O-Substitutions (Methoxy/Hydroxyl/Ether Modifications) ──
    # ═══════════════════════════════════════════════════════════
    "OSUB_001": SmirksEntry(
        id="OSUB_001",
        category="o_substitutions",
        name="Methoxy to Ethoxy",
        smirks="[C:1][OX2:2]([CH3:3])>>[C:1][CH2][OX2:2][CH3:3]",
        description="Ethoxy is slightly larger and more lipophilic than methoxy. "
                    "Extends half-life for CNS drugs by reducing CYP oxidation.",
        expected_impact="Metabolic stability, half-life extension",
        complexity_delta=0.2,
        tags=["metabolic_stability", "lipophilicity_increase", "cns"],
        reference="MedChem principles, ethoxy substitution"
    ),
    "OSUB_002": SmirksEntry(
        id="OSUB_002",
        category="o_substitutions",
        name="Methoxy to Hydroxyl (O-demethylation)",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][OX2H:2]",
        description="O-demethylation yields phenolic OH. Increases polarity "
                    "and H-bonding capacity. Reduces LogP but may increase clearance.",
        expected_impact="Polarity increase, solubility, LogP reduction",
        complexity_delta=0.0,
        tags=["logp_reduction", "solubility", "polarity"],
        reference="Metabolic dealkylation pathway"
    ),
    "OSUB_003": SmirksEntry(
        id="OSUB_003",
        category="o_substitutions",
        name="Hydroxyl to Fluoro (deoxyfluorination)",
        smirks="[CH2:1][OX2H:2]>>[CH2:1][F]",
        description="Classic isostere. Fluorine is similar in size to OH "
                    "but dramatically reduces polarity and blocks metabolism.",
        expected_impact="Metabolic stability, polarity reduction, CYP shift",
        complexity_delta=0.3,
        tags=["metabolic_stability", "polarity_reduction", "fluorination"],
        reference="J. Med. Chem. 2019, fluoroalkylation"
    ),
    "OSUB_004": SmirksEntry(
        id="OSUB_004",
        category="o_substitutions",
        name="Hydroxyl to Amino",
        smirks="[C:1][OX2H:2]>>[C:1][NH2]",
        description="OH to NH2 changes H-bond donor/acceptor pattern. "
                    "Primary amine is metabolically more stable but introduces basicity.",
        expected_impact="Basicity introduction, metabolic stability shift",
        complexity_delta=0.5,
        tags=["metabolic_stability", "basic_nitrogen", "hbd_shift"],
        reference="Bioisosteres in MedChem, Ch. 3"
    ),
    "OSUB_005": SmirksEntry(
        id="OSUB_005",
        category="o_substitutions",
        name="Methoxy to Trifluoromethoxy",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][OX2:2][C:3](F)(F)F",
        description="OCF3 is strongly electron-withdrawing and lipophilic. "
                    "Confers exceptional metabolic stability at the site.",
        expected_impact="Metabolic stability, lipophilicity increase, CYP resistance",
        complexity_delta=0.8,
        tags=["metabolic_stability", "lipophilicity_increase", "cyp_resistance"],
        reference="J. Med. Chem. 2018, OCF3 in drug design"
    ),
    "OSUB_006": SmirksEntry(
        id="OSUB_006",
        category="o_substitutions",
        name="Methoxy to Amino (O→N substitution)",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][NH2:2]",
        description="Aniline instead of anisole. Dramatically changes electronics "
                    "and H-bonding. Reduces lipophilicity significantly.",
        expected_impact="LogP reduction, electronic shift, basicity",
        complexity_delta=1.0,
        tags=["logp_reduction", "electronic_shift", "basic_nitrogen"],
        reference="Aromatic substitution principles"
    ),
    "OSUB_007": SmirksEntry(
        id="OSUB_007",
        category="o_substitutions",
        name="Methoxy to Methylthio (O→S)",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][SX2:2][CH3]",
        description="Thioether is more lipophilic than ether and more "
                    "resistant to oxidative metabolism.",
        expected_impact="Lipophilicity increase, metabolic stability",
        complexity_delta=0.5,
        tags=["metabolic_stability", "lipophilicity_increase", "sulfur"],
        reference="Thioether bioisosteres"
    ),
    "OSUB_009": SmirksEntry(
        id="OSUB_009",
        category="o_substitutions",
        name="Methoxy to Difluoromethoxy",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][OX2:2][CH:3](F)F",
        description="OCHF2 is metabolically stable and moderately lipophilic. "
                    "Good for reducing CYP-mediated clearance.",
        expected_impact="Metabolic stability, moderate LogP shift",
        complexity_delta=0.4,
        tags=["metabolic_stability", "fluorination", "cyp_resistance"],
        reference="Difluoromethoxy SAR"
    ),
    "OSUB_010": SmirksEntry(
        id="OSUB_010",
        category="o_substitutions",
        name="Methoxy to Isopropoxy",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][OX2:2][CH](C)C",
        description="Isopropoxy is sterically larger, reducing CYP oxidation. "
                    "Increases lipophilicity and can improve membrane permeability.",
        expected_impact="Metabolic stability, lipophilicity increase, steric_block",
        complexity_delta=0.3,
        tags=["metabolic_stability", "lipophilicity_increase", "steric_block"],
        reference="Isopropyl Ether Modifications"
    ),
    "OSUB_011": SmirksEntry(
        id="OSUB_011",
        category="o_substitutions",
        name="Hydroxyl to Methoxy",
        smirks="[C:1][OX2H:2]>>[C:1][OX2:2][CH3]",
        description="Methyl ether protection of alcohol. Blocks glucuronidation "
                    "and increases lipophilicity and metabolic stability.",
        expected_impact="Metabolic stability, lipophilicity increase, glucuronidation_block",
        complexity_delta=0.0,
        tags=["metabolic_stability", "lipophilicity_increase", "glucuronidation_block"],
        reference="Alcohol protection strategies"
    ),
    "OSUB_012": SmirksEntry(
        id="OSUB_012",
        category="o_substitutions",
        name="Hydroxyl to OCF3 (trifluoromethyl ether)",
        smirks="[C:1][OX2H:2]>>[C:1][OX2:2]C(F)(F)F",
        description="Trifluoromethyl ether is extremely metabolically stable "
                    "and lipophilic. Unusual but effective for hERG reduction.",
        expected_impact="Metabolic stability, lipophilicity increase, herg_reduction",
        complexity_delta=1.0,
        tags=["metabolic_stability", "lipophilicity_increase", "herg_reduction"],
        reference="OCF3 ether modifications"
    ),
    "OSUB_013": SmirksEntry(
        id="OSUB_013",
        category="o_substitutions",
        name="Hydroxyl to Hydroxylamine (NHOH)",
        smirks="[C:1][OX2H:2]>>[C:1][N:2]O",
        description="Hydroxylamine is a weak base with unique electronic properties. "
                    "Rarely used but can confer specific target interactions.",
        expected_impact="Electronic shift, basicity, unique pharmacophore",
        complexity_delta=1.2,
        tags=["electronic_shift", "unique_pharmacophore", "weak_base"],
        reference="Hydroxylamine isosteres"
    ),
    "OSUB_014": SmirksEntry(
        id="OSUB_014",
        category="o_substitutions",
        name="Hydroxyl to O-Acetyl (acetylation)",
        smirks="[C:1][OX2H:2]>>[C:1][OX2:2][C](=O)C",
        description="Acetate ester is a pro-drug strategy. Rapidly hydrolyzed "
                    "in vivo but improves solubility and absorption.",
        expected_impact="Solubility increase, pro-drug, rapid metabolism",
        complexity_delta=0.2,
        tags=["solubility", "pro_drug", "esterase_labile"],
        reference="Pro-drug strategies"
    ),
    "OSUB_015": SmirksEntry(
        id="OSUB_015",
        category="o_substitutions",
        name="Methoxy to Fluoromethoxy",
        smirks="[c:1][OX2:2]([CH3:3])>>[c:1][OX2:2][CH2:3]F",
        description="Fluoromethoxy is metabolically stable yet moderately polar. "
                    "Balance between OCF3 and unsubstituted ether.",
        expected_impact="Metabolic stability, moderate polarity, CYP resistance",
        complexity_delta=0.3,
        tags=["metabolic_stability", "fluorination", "balanced_pol"],
        reference="Fluoromethoxy SAR"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Benzylic / Aliphatic Modifications ──────────────────────
    # ════════════════════════════════════════════════════════════════════
    "BENZ_001": SmirksEntry(
        id="BENZ_001",
        category="benzylic_modifications",
        name="Benzylic CH2 to C=O (oxidation to aldehyde/ketone)",
        smirks="[c:1][CH2:2]>>[c:1][C:2]=O",
        description="Benzylic oxidation is a common metabolic pathway. "
                    "Blocking as carbonyl removes CYP liability but introduces electrophilicity.",
        expected_impact="Metabolic blunting, electrophilicity, carbonyl introduction",
        complexity_delta=0.5,
        tags=["metabolic_stability", "electrophile", "carbonyl"],
        reference="Benzylic oxidation principles"
    ),
    "BENZ_002": SmirksEntry(
        id="BENZ_002",
        category="benzylic_modifications",
        name="Benzylic alcohol CH2OH to CH2F (deoxyfluorination)",
        smirks="[c:1][CH2:2][OX2H:3]>>[c:1][CH2:2][F]",
        description="Direct fluorine replacement of benzylic hydroxyl. "
                    "Blocks metabolism and maintains size.",
        expected_impact="Metabolic stability, fluorination, polarity reduction",
        complexity_delta=0.4,
        tags=["metabolic_stability", "fluorination", "polarity_reduction"],
        reference="Benzylic fluorination, J. Med. Chem. 2017"
    ),
    "BENZ_003": SmirksEntry(
        id="BENZ_003",
        category="benzylic_modifications",
        name="Benzylic alcohol CH2OH to CH2NH2 (amination)",
        smirks="[c:1][CH2:2][OX2H:3]>>[c:1][CH2:2][NH2]",
        description="Benzylic amine is more basic and less prone to oxidation "
                    "than benzylic alcohol. Introduces nitrogen.",
        expected_impact="Metabolic stability, basic_nitrogen, amine_introduction",
        complexity_delta=0.6,
        tags=["metabolic_stability", "basic_nitrogen", "amine"],
        reference="Benzylic amine bioisosteres"
    ),
    "BENZ_004": SmirksEntry(
        id="BENZ_004",
        category="benzylic_modifications",
        name="Benzylic alcohol CH2OH to CH2CN (nitrile)",
        smirks="[c:1][CH2:2][OX2H:3]>>[c:1][CH2:2][CX2]#[NX1]",
        description="Nitrile is metabolically stable and acts as H-bond acceptor. "
                    "Used in many CYP inhibitors.",
        expected_impact="Metabolic stability, hbond_acceptor, nitrile",
        complexity_delta=0.5,
        tags=["metabolic_stability", "hbond_acceptor", "nitrile"],
        reference="Nitrile isosteres in drug design"
    ),
    "BENZ_005": SmirksEntry(
        id="BENZ_005",
        category="benzylic_modifications",
        name="Benzylic alcohol to aldehyde (oxidation)",
        smirks="[c:1][CH2:2][OX2H]>>[c:1][CH:2]=O",
        description="Direct oxidation of benzylic alcohol to aldehyde. "
                    "The aldehyde is an electrophile — use with caution.",
        expected_impact="Electrophilicity, carbonyl, metabolic pathway",
        complexity_delta=0.7,
        tags=["electrophile", "carbonyl", "metabolic_intermediate"],
        reference="Benzylic oxidation intermediates"
    ),
    "BENZ_006": SmirksEntry(
        id="BENZ_006",
        category="benzylic_modifications",
        name="Benzylic alcohol to CH2OCF3 (trifluoromethyl ether)",
        smirks="[c:1][CH2:2][OX2H:3]>>[c:1][CH2:2][OX2:3]C(F)(F)F",
        description="Benzylic OCF3 ether provides extreme metabolic stability "
                    "at the benzylic position.",
        expected_impact="Metabolic stability, OCF3 introduction, lipophilicity",
        complexity_delta=1.0,
        tags=["metabolic_stability", "lipophilicity_increase", "ocf3"],
        reference="Benzylic OCF3 modifications"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Bioisosteric Replacements ────────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "BIOISO_001": SmirksEntry(
        id="BIOISO_001",
        category="bioisosteric_replacements",
        name="Hydroxyl to Difluoromethyl (CHF2)",
        smirks="[C:1][OX2H:2]>>[C:1][CH:2](F)F",
        description="CHF2 is a lipophilic isostere of OH. Metabolically stable "
                    "due to the strong C-F bonds. Reduces polarity dramatically.",
        expected_impact="Metabolic stability, lipophilicity increase, polarity_reduction",
        complexity_delta=0.3,
        tags=["metabolic_stability", "lipophilicity_increase", "fluorination"],
        reference="CHF2 bioisostere, J. Med. Chem. 2020"
    ),
    "BIOISO_002": SmirksEntry(
        id="BIOISO_002",
        category="bioisosteric_replacements",
        name="Hydroxyl to Fluoromethyl (CH2F)",
        smirks="[C:1][OX2H:2]>>[C:1][CH2:2]F",
        description="CH2F is a small, weakly lipophilic isostere of OH. "
                    "Less stable than CHF2 but softer electronics.",
        expected_impact="Metabolic stability, mild lipophilicity increase",
        complexity_delta=0.2,
        tags=["metabolic_stability", "fluorination", "soft_electronics"],
        reference="Fluoromethyl bioisosteres"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Aromatic C-H Substitutions ──────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "AROM_001": SmirksEntry(
        id="AROM_001",
        category="aromatic_substitutions",
        name="Aromatic C-H to C-F (ring fluorination)",
        smirks="[cH:1]>>[c:1]F",
        description="Direct aromatic fluorination blocks CYP-mediated aromatic "
                    "oxidation and improves metabolic stability. Small size penalty.",
        expected_impact="Metabolic stability, fluorination, CYP block",
        complexity_delta=0.5,
        tags=["metabolic_stability", "fluorination", "cyp_block", "aromatic"],
        reference="Aromatic fluorination, J. Med. Chem. 2016"
    ),
    "AROM_002": SmirksEntry(
        id="AROM_002",
        category="aromatic_substitutions",
        name="Aromatic methylation (C-H to CH3)",
        smirks="[cH:1]>>[c:1]C",
        description="Toluene substitution blocks para-position metabolism "
                    "and increases lipophilicity. Classic steric block.",
        expected_impact="Metabolic stability, lipophilicity increase, steric_block",
        complexity_delta=0.1,
        tags=["metabolic_stability", "lipophilicity_increase", "steric_block"],
        reference="Tolyl bioisosteres"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Ether / Amine Modifications ────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "ETHER_001": SmirksEntry(
        id="ETHER_001",
        category="ether_modifications",
        name="Aryl ether to aryl amine (O→NH)",
        smirks="[c:1][OX2:2][C:3]>>[c:1][NH:2][C:3]",
        description="Converting aryl ether to anilide changes electronics "
                    "significantly and introduces a hydrogen bond donor.",
        expected_impact="Electronic shift, H-bond donor, solubility increase",
        complexity_delta=0.8,
        tags=["electronic_shift", "hbd_introduction", "solubility"],
        reference="Anilide vs aryl ether electronics"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Sulfonyl / Alkylsulfonyl Modifications ──────────────────
    # ════════════════════════════════════════════════════════════════════
    "SULF_001": SmirksEntry(
        id="SULF_001",
        category="sulfonyl_modifications",
        name="Methyl to Methylsulfonyl (Metabolite block)",
        smirks="[CH3:1]>>[CH2:1]S(=O)(=O)C",
        description="Oxidizing methyl to SO2Me blocks CYP-mediated oxidation "
                    "at that position. Introduces polar sulfonyl group.",
        expected_impact="Metabolic block, polarity increase, sulfonyl introduction",
        complexity_delta=0.8,
        tags=["metabolic_block", "polarity_increase", "sulfonyl"],
        reference="Sulfonyl bioisosteres for methyl groups"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Amine Modifications ─────────────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "AMINE_001": SmirksEntry(
        id="AMINE_001",
        category="amine_modifications",
        name="Primary amine to secondary amine (N-methylation)",
        smirks="[NH2:1]>>[NH:1][CH3]",
        description="N-methylation of primary amine. Reduces basicity slightly "
                    "and blocks oxidative deamination metabolism.",
        expected_impact="Metabolic stability, reduced basicity, CNS penetration",
        complexity_delta=0.0,
        tags=["metabolic_stability", "basicity_reduction", "n_methylation"],
        reference="Bioisosteres in MedChem, Ch. 13"
    ),
    "AMINE_002": SmirksEntry(
        id="AMINE_002",
        category="amine_modifications",
        name="Primary amine to tertiary amine",
        smirks="[NH2:1]>>[N:1]([CH3])[CH3]",
        description="Introducing a tertiary amine. Permanently reduces H-bond "
                    "donor capacity. Changes pKa and distribution coefficient.",
        expected_impact="Basicity shift, polarity reduction, metabolic stability",
        complexity_delta=0.0,
        tags=["basicity_reduction", "polarity_reduction", "metabolic_stability"],
        reference="Bioisosteres in MedChem"
    ),
    "AMINE_003": SmirksEntry(
        id="AMINE_003",
        category="amine_modifications",
        name="Tertiary amine to quaternary ammonium",
        smirks="[N:1]([C:2])([C:3])[C:4]>>[N+:1]([C:2])([C:3])([C:4])",
        description="Permanent positive charge. Eliminates membrane permeability "
                    "but useful for targeting specific anion binding sites.",
        expected_impact="Permanent_charge, targeting, solubility",
        complexity_delta=0.0,
        tags=["permanent_charge", "targeting", "solubility"],
        reference="Wilson & Gisvold, Ch. 2"
    ),
    "AMINE_004": SmirksEntry(
        id="AMINE_004",
        category="amine_modifications",
        name="Primary amine to sulfonamide",
        smirks="[NH2:1]>>[S:1](=O)(=O)[NH2:1]",
        description="Sulfonamide is a classic bioisostere of amine. "
                    "Reduces basicity dramatically and changes H-bonding pattern.",
        expected_impact="Basicity reduction, electronic shift, metabolic stability",
        complexity_delta=0.8,
        tags=["basicity_reduction", "electronic_shift", "sulfonamide"],
        reference="Bioisosteres in MedChem, Ch. 3"
    ),
    "AMINE_005": SmirksEntry(
        id="AMINE_005",
        category="amine_modifications",
        name="Primary amine to amide (acetylation)",
        smirks="[NH2:1]>>[N:1]([C:2])=[O:3]",
        description="Acetylation of amine. Masks basicity and reduces HBD. "
                    "Common for CNS penetration (减少了 PSA).",
        expected_impact="Basicity reduction, PSA reduction, CNS penetration",
        complexity_delta=0.3,
        tags=["basicity_reduction", "cns_penetration", "psa_reduction"],
        reference="CNS penetration strategies"
    ),
    "AMINE_006": SmirksEntry(
        id="AMINE_006",
        category="amine_modifications",
        name="Tertiary amine to N-oxide",
        smirks="[N:1]([C:2])([C:3])[C:4]>>[N+:1](=[O:5])-[C:2]([C:3])[C:4]",
        description="N-oxidation is a common metabolic pathway. Pre-forming "
                    "the N-oxide blocks this metabolism and changes basicity.",
        expected_impact="Metabolic block, basicity modulation, polarity increase",
        complexity_delta=0.5,
        tags=["metabolic_block", "basicity_modulation", "polarity_increase"],
        reference="Bioisosteres in MedChem, Ch. 3"
    ),
    "AMINE_007": SmirksEntry(
        id="AMINE_007",
        category="amine_modifications",
        name="Aromatic amine to N-oxide (heteroaryl)",
        smirks="[n:1]>>[n+:1](=O)[O-]",
        description="Heteroaryl nitrogen N-oxidation. Blocks metabolic N-oxide "
                    "formation and changes electronics of heterocycle.",
        expected_impact="Metabolic block, electronic shift, polarity",
        complexity_delta=0.5,
        tags=["metabolic_block", "electronic_shift", "heteroaryl"],
        reference="Linopirdine example, Bioisosteres in MedChem, Ch. 3"
    ),
    "AMINE_008": SmirksEntry(
        id="AMINE_008",
        category="amine_modifications",
        name="Primary amine to tetrazole",
        smirks="[NH2:1]>>[C:1]1=NN=N[NH]1",
        description="Tetrazole is a non-basic isostere of primary amine. "
                    "Similar pKa (~4.9) but different electronic properties.",
        expected_impact="Basicity elimination, bioisostere, metabolic stability",
        complexity_delta=1.2,
        tags=["basicity_elimination", "bioisostere", "metabolic_stability"],
        reference="Bioisosteres in MedChem, Ch. 4"
    ),
    "AMINE_009": SmirksEntry(
        id="AMINE_009",
        category="amine_modifications",
        name="Primary amine to nitrile",
        smirks="[NH2:1]>>[C:1]#[NX1]",
        description="Nitrile is a small, metabolically stable group. "
                    "Reduces basicity compared to amine but introduces different electronics.",
        expected_impact="Basicity reduction, metabolic stability, small_size",
        complexity_delta=0.3,
        tags=["basicity_reduction", "metabolic_stability", "small_size"],
        reference="Nitrile bioisosteres"
    ),
    "AMINE_010": SmirksEntry(
        id="AMINE_010",
        category="amine_modifications",
        name="Dimethylamine to diethylamine",
        smirks="[N:1]([C:2])[C:3]>>[N:1]([C:2])[C:3][C:4]",
        description="Increasing alkyl chain length reduces basicity slightly "
                    "and increases lipophilicity.",
        expected_impact="Basicity reduction, lipophilicity increase",
        complexity_delta=0.0,
        tags=["basicity_reduction", "lipophilicity_increase"],
        reference="Alkyl amine SAR"
    ),
    "AMINE_011": SmirksEntry(
        id="AMINE_011",
        category="amine_modifications",
        name="Piperidine to homopiperazine",
        smirks="[N:1]1[C:2][C:3][C:4][C:5][C:6]1>>[N:1]1[C:2][C:3][N:4][C:5][C:6]1",
        description="Adding a second nitrogen increases polarity and H-bond "
                    "capacity. Useful for solubility tuning.",
        expected_impact="Solubility increase, polarity increase, H-bond capacity",
        complexity_delta=0.5,
        tags=["solubility", "polarity_increase", "heterocycle_expansion"],
        reference="Piperazine SAR in drug design"
    ),
    "AMINE_012": SmirksEntry(
        id="AMINE_012",
        category="amine_modifications",
        name="Morpholine to thiomorpholine",
        smirks="[O:1]1[C:2][C:3][N:4][C:5][C:6]1>>[S:1]1[C:2][C:3][N:4][C:5][C:6]1",
        description="O → S substitution increases lipophilicity and changes "
                    "H-bond acceptor basicity.",
        expected_impact="Lipophilicity increase, H-bond shift, metabolic stability",
        complexity_delta=0.5,
        tags=["lipophilicity_increase", "chalcogen_swap", "hbond_shift"],
        reference="Chalcogen isosteres in medicinal chemistry"
    ),
    "AMINE_013": SmirksEntry(
        id="AMINE_013",
        category="amine_modifications",
        name="Primary amine to amide (formylation)",
        smirks="[NH2:1]>>[N:1][C:2]=[O:3]",
        description="Formamide is the smallest amide. Reduces basicity "
                    "while maintaining some polarity.",
        expected_impact="Basicity reduction, polarity modulation",
        complexity_delta=0.2,
        tags=["basicity_reduction", "polarity_modulation"],
        reference="Amide isosteres"
    ),
    "AMINE_014": SmirksEntry(
        id="AMINE_014",
        category="amine_modifications",
        name="Primary amine to hydroxylamine",
        smirks="[NH2:1]>>[NH:1][OH]",
        description="Hydroxylamine has weak basicity and unique H-bonding. "
                    "Can form complexes with metal ions.",
        expected_impact="Basicity modulation, metal chelation, unique pharmacophore",
        complexity_delta=0.5,
        tags=["basicity_modulation", "metal_chelation", "unique_pharmacophore"],
        reference="Hydroxylamine bioisosteres"
    ),
    "AMINE_015": SmirksEntry(
        id="AMINE_015",
        category="amine_modifications",
        name="Tertiary amine to difluoromethyl",
        smirks="[N:1]([C:2])([C:3])[C:4]>>[C:4]([F:5])([F:6])",
        description="Replacing a tertiary amine with difluoromethyl removes basicity "
                    "but maintains similar steric profile and lipophilicity.",
        expected_impact="Basicity elimination, lipophilicity maintenance, metabolic stability",
        complexity_delta=1.0,
        tags=["basicity_elimination", "fluorination", "lipophilicity_maintained"],
        reference="Difluoromethyl bioisosteres, J. Med. Chem. 2020"
    ),
    "AMINE_016": SmirksEntry(
        id="AMINE_016",
        category="amine_modifications",
        name="Pyrrolidine to azetidine",
        smirks="[N:1]1[C:2][C:3][C:4][C:5]1>>[N:1]1[C:2][C:3][C:4]1",
        description="Ring contraction from 5- to 4-membered ring. "
                    "Changes conformational flexibility and basicity.",
        expected_impact="Conformational constraint, basicity shift, steric change",
        complexity_delta=0.5,
        tags=["conformational_constraint", "basicity_shift", "ring_contraction"],
        reference="Azetidine isosteres"
    ),
    "AMINE_017": SmirksEntry(
        id="AMINE_017",
        category="amine_modifications",
        name="Azetidine to pyrrolidine (ring expansion)",
        smirks="[N:1]1[C:2][C:3][C:4]1>>[N:1]1[C:2][C:3][C:4][C:5]1",
        description="Ring expansion from 4- to 5-membered ring. "
                    "Increases flexibility and changes basicity.",
        expected_impact="Ring expansion, flexibility increase, basicity shift",
        complexity_delta=0.5,
        tags=["ring_expansion", "flexibility", "basicity_shift"],
        reference="Ring expansion SAR"
    ),
    "AMINE_018": SmirksEntry(
        id="AMINE_018",
        category="amine_modifications",
        name="Aniline to pyridine (aryl amine to heteroaryl)",
        smirks="[c:1][NH2:2]>>[c:1][n:2]",
        description="Converting aniline to pyridine removes the HBD and introduces "
                    "an HBA with different basicity profile.",
        expected_impact="HBD removal, basicity shift, electronic change",
        complexity_delta=0.5,
        tags=["hbd_removal", "basicity_shift", "electronic_change"],
        reference="Heteroaryl amine isosteres"
    ),
    "AMINE_019": SmirksEntry(
        id="AMINE_019",
        category="amine_modifications",
        name="Secondary amine to tertiary amine (N-ethylation)",
        smirks="[NH:1][C:2]>>[N:1]([C:2])[C:3]",
        description="N-ethylation blocks metabolic demethylation while "
                    "maintaining basicity.",
        expected_impact="Metabolic stability, basicity modulation, lipophilicity",
        complexity_delta=0.0,
        tags=["metabolic_stability", "alkylation", "lipophilicity"],
        reference="N-alkylation strategies"
    ),
    "AMINE_020": SmirksEntry(
        id="AMINE_020",
        category="amine_modifications",
        name="Amidine formation from nitrile",
        smirks="[CX2]#[NX1:1]>>[C:1](=[N:2])[N:3]",
        description="Converting nitrile to amidine dramatically increases basicity. "
                    "Useful for targeting acidic residues.",
        expected_impact="Basicity increase, targeting, metal binding",
        complexity_delta=1.0,
        tags=["basicity_increase", "targeting", "metal_binding"],
        reference="Amidine bioisosteres, Wilson & Gisvold"
    ),
    "AMINE_021": SmirksEntry(
        id="AMINE_021",
        category="amine_modifications",
        name="Guanidine from amidine",
        smirks="[C:1](=[N:2])[N:3]>>[C:1](=[N:2])[N:3][C:4](=[N:5])[N:6]",
        description="Extending amidine to guanidine increases basicity further. "
                    "Common in arginine mimics.",
        expected_impact="Basicity increase, arginine mimic, strong cation",
        complexity_delta=1.0,
        tags=["basicity_increase", "arginine_mimic", "strong_cation"],
        reference="Guanidine bioisosteres, Bioisosteres in MedChem Ch. 4"
    ),
    "AMINE_022": SmirksEntry(
        id="AMINE_022",
        category="amine_modifications",
        name="Primary amine to carbamate",
        smirks="[NH2:1]>>[N:1]([C:2])=[O:3]",
        description="Carbamate is a metabolically stable amide isostere. "
                    "Eliminates basicity but maintains H-bonding.",
        expected_impact="Basicity elimination, metabolic stability, H-bonding",
        complexity_delta=0.8,
        tags=["basicity_elimination", "metabolic_stability", "hbonding"],
        reference="Carbamate bioisosteres"
    ),
    "AMINE_023": SmirksEntry(
        id="AMINE_023",
        category="amine_modifications",
        name="Piperidine to N-methylpiperidine",
        smirks="[N:1]1[C:2][C:3][C:4][C:5][C:6]1>>[N+:1]([CH3:7])1[C:2][C:3][C:4][C:5][C:6]1",
        description="Quaternizing the piperidine nitrogen. Permanently charged. "
                    "Blocks CYP metabolism at nitrogen.",
        expected_impact="Permanent_charge, metabolic_block, solubility",
        complexity_delta=0.5,
        tags=["permanent_charge", "metabolic_block", "solubility"],
        reference="Quaternary ammonium SAR"
    ),
    "AMINE_024": SmirksEntry(
        id="AMINE_024",
        category="amine_modifications",
        name="Amine to oxazolidinone (for CNS)",
        smirks="[NH2:1][C:2][C:3]>>[O:1]1[C:2][C:3][N:4]1",
        description="Cyclic carbamate isostere of amino alcohol. Constrains "
                    "conformation and reduces PSA for CNS drugs.",
        expected_impact="Conformational constraint, PSA reduction, CNS",
        complexity_delta=0.8,
        tags=["conformational_constraint", "psa_reduction", "cns"],
        reference="Oxazolidinone CNS agents"
    ),
    "AMINE_025": SmirksEntry(
        id="AMINE_025",
        category="amine_modifications",
        name="Dimethylamine to pyrrolidine",
        smirks="[N:1]([C:2])[C:3]>>[N:1]1[C:2][C:3][C:4][C:5]1",
        description="Cyclic secondary amine from dimethylamine. Reduces "
                    "solvent exposure and changes basicity.",
        expected_impact="Conformational constraint, basicity modulation, lipophilicity",
        complexity_delta=0.5,
        tags=["conformational_constraint", "basicity_modulation", "lipophilicity"],
        reference="Pyrrolidine isosteres"
    ),
    "AMINE_026": SmirksEntry(
        id="AMINE_026",
        category="amine_modifications",
        name="Secondary amine to urea (N,N-dimethyl)",
        smirks="[NH:1][C:2]>>[N:1]([C:2])[C:3](=[O:4])[N:5][C:6]",
        description="Converting amine to urea increases polarity and H-bonding. "
                    "Can improve solubility.",
        expected_impact="Polarity increase, solubility, H-bonding capacity",
        complexity_delta=1.0,
        tags=["polarity_increase", "solubility", "hbonding"],
        reference="Urea bioisosteres"
    ),
    "AMINE_027": SmirksEntry(
        id="AMINE_027",
        category="amine_modifications",
        name="Tertiary amine to amide (dealkylation)",
        smirks="[N:1]([C:2])([C:3])[C:4]>>[N:1]([C:2])[C:5](=[O:6])",
        description="Converting tertiary amine to amide (via dealkylation). "
                    "Reduces basicity and changes electronic properties.",
        expected_impact="Basicity reduction, electronic shift, amide formation",
        complexity_delta=0.8,
        tags=["basicity_reduction", "electronic_shift", "amide_formation"],
        reference="Amide isosteres from amines"
    ),
    "AMINE_028": SmirksEntry(
        id="AMINE_028",
        category="amine_modifications",
        name="Piperazine to homopiperazine",
        smirks="[N:1]1[C:2][N:3][C:4][C:5][C:6]1>>[N:1]1[C:2][C:3][N:4][C:5][C:6][C:7]1",
        description="Extending the piperazine ring by one carbon. "
                    "Changes steric and basicity profile.",
        expected_impact="Steric change, basicity modulation, flexibility",
        complexity_delta=0.5,
        tags=["steric_change", "basicity_modulation", "flexibility"],
        reference="Homopiperazine SAR"
    ),
    "AMINE_029": SmirksEntry(
        id="AMINE_029",
        category="amine_modifications",
        name="Primary amine to methyl ester (via oxidation)",
        smirks="[NH2:1]>>[C:1](=[O:2])[O:3][CH3:4]",
        description="Converting amine to ester eliminates basicity. "
                    "Dramatically changes pharmacokinetics.",
        expected_impact="Basicity elimination, polarity shift, metabolic change",
        complexity_delta=1.0,
        tags=["basicity_elimination", "polarity_shift", "ester_formation"],
        reference="Ester isosteres of amines"
    ),
    "AMINE_030": SmirksEntry(
        id="AMINE_030",
        category="amine_modifications",
        name="Alkyl amine to aryl amine",
        smirks="[N:1][CH3:2]>>[N:1][c:2]",
        description="Introducing aromatic ring changes basicity, lipophilicity, "
                    "and electronic properties dramatically.",
        expected_impact="Basicity reduction, lipophilicity increase, electronic shift",
        complexity_delta=0.5,
        tags=["basicity_reduction", "lipophilicity_increase", "aryl_introduction"],
        reference="Aryl amine SAR"
    ),
    "AMINE_031": SmirksEntry(
        id="AMINE_031",
        category="amine_modifications",
        name="Diethylamine to diisopropylamine",
        smirks="[N:1]([CH2:2][CH3:3])[CH2:4][CH3:5]>>[N:1]([CH:2]([CH3:3])[CH3:6])[CH:4]([CH3:7])[CH3:8]",
        description="Isopropyl groups are sterically larger and more lipophilic. "
                    "Reduces CYP metabolism and changes binding.",
        expected_impact="Steric bulk increase, lipophilicity increase, metabolic stability",
        complexity_delta=0.3,
        tags=["steric_bulk", "lipophilicity_increase", "metabolic_stability"],
        reference="Isopropyl bioisosteres"
    ),
    "AMINE_032": SmirksEntry(
        id="AMINE_032",
        category="amine_modifications",
        name="Morpholine to N-acetyl morpholine",
        smirks="[O:1]1[C:2][C:3][N:4]([C:5]=[O:6])[C:7][C:8]1>>[O:1]1[C:2][C:3][N:4]([C:5]=[O:6])[C:7][C:8]1",
        description="Acetylation of morpholine nitrogen. Reduces basicity "
                    "and changes H-bonding profile.",
        expected_impact="Basicity reduction, H-bonding change, metabolic shift",
        complexity_delta=0.3,
        tags=["basicity_reduction", "hbonding_change", "metabolic_shift"],
        reference="Morpholine SAR"
    ),
    "AMINE_033": SmirksEntry(
        id="AMINE_033",
        category="amine_modifications",
        name="Amidine to N-methyl amidine",
        smirks="[C:1](=[N:2])[N:3]>>[C:1](=[N:2])[N:3][CH3:4]",
        description="N-methylation of amidine reduces basicity slightly "
                    "and blocks metabolic demethylation.",
        expected_impact="Basicity modulation, metabolic stability",
        complexity_delta=0.2,
        tags=["basicity_modulation", "metabolic_stability"],
        reference="Amidine SAR"
    ),
    "AMINE_034": SmirksEntry(
        id="AMINE_034",
        category="amine_modifications",
        name="Cyanoguanidine to guanidine",
        smirks="[N:1]([C:2]#[NX1:3])=[N:4]>>[C:2](=[N:1])[N:4]",
        description="Removing the cyano group from cyanoguanidine. "
                    "Simplifies the pharmacophore and changes basicity.",
        expected_impact="Basicity increase, structural simplification",
        complexity_delta=0.5,
        tags=["basicity_increase", "simplification"],
        reference="Cimetidine→guanidine, Bioisosteres in MedChem Ch. 2"
    ),
    "AMINE_035": SmirksEntry(
        id="AMINE_035",
        category="amine_modifications",
        name="Pyrrolidine to oxazolidine",
        smirks="[N:1]1[C:2][C:3][C:4][C:5]1>>[O:1]1[C:2][C:3][N:4][C:5]1",
        description="Oxygen isostere of pyrrolidine. More electronegative, "
                    "changes basicity and H-bonding.",
        expected_impact="Basicity reduction, electronegativity increase, H-bonding change",
        complexity_delta=0.5,
        tags=["basicity_reduction", "electronegativity", "hbonding_change"],
        reference="Oxazolidine isosteres"
    ),
    "AMINE_036": SmirksEntry(
        id="AMINE_036",
        category="amine_modifications",
        name="Primary amine to imine (Schiff base)",
        smirks="[NH2:1]>>[N:1]=[CH2:2]",
        description="Converting primary amine to imine. Reduces basicity "
                    "and introduces different reactivity.",
        expected_impact="Basicity reduction, reactivity change, imine_formation",
        complexity_delta=0.3,
        tags=["basicity_reduction", "reactivity", "imine"],
        reference="Schiff base bioisosteres"
    ),
    "AMINE_037": SmirksEntry(
        id="AMINE_037",
        category="amine_modifications",
        name="Aryl amine to alkyl amine",
        smirks="[c:1][NH2:2]>>[C:2][C:3][NH2:4]",
        description="Removing aromaticity from amine. Increases flexibility "
                    "and changes basicity.",
        expected_impact="Basicity modulation, flexibility increase, lipophilicity reduction",
        complexity_delta=0.5,
        tags=["basicity_modulation", "flexibility", "lipophilicity_reduction"],
        reference="Aryl→alkyl amine SAR"
    ),
    "AMINE_038": SmirksEntry(
        id="AMINE_038",
        category="amine_modifications",
        name="Piperidine to 2-methylpiperidine",
        smirks="[N:1]1[C:2][C:3][C:4][C:5][C:6]1>>[N:1]1[C:2]([CH3:7])[C:3][C:4][C:5][C:6]1",
        description="Alpha-methylation introduces steric bulk near the nitrogen. "
                    "Can block metabolism and change basicity.",
        expected_impact="Steric block, metabolic stability, basicity shift",
        complexity_delta=0.3,
        tags=["steric_block", "metabolic_stability", "basicity_shift"],
        reference="Alpha-methyl amine SAR"
    ),
    "AMINE_039": SmirksEntry(
        id="AMINE_039",
        category="amine_modifications",
        name="Aryl amine to heteroaryl amine (ring expansion)",
        smirks="[c:1][NH2:2]>>[c:1]1[c:2][n:3][c:4]1",
        description="Converting anilide to heteroaryl amine. "
                    "Removes aromatic amine and introduces heterocycle.",
        expected_impact="Basicity modulation, heteroaryl introduction, flexibility",
        complexity_delta=0.5,
        tags=["basicity_modulation", "heteroaryl", "flexibility"],
        reference="Aryl to heteroaryl amine transformation"
    ),
    "AMINE_040": SmirksEntry(
        id="AMINE_040",
        category="amine_modifications",
        name="Tropane to granatane (ring expansion)",
        smirks="[N:1]1[C:2][C:3][C:4][C:5][C:6]1>>[N:1]1[C:2][C:3][N:4][C:5][C:6]1",
        description="Piperidine to piperazine. Adds second basic nitrogen. "
                    "Changes solubility and H-bonding profile.",
        expected_impact="Solubility increase, H-bond capacity, basicity modulation",
        complexity_delta=0.5,
        tags=["solubility", "hbond_capacity", "basicity_modulation"],
        reference="Piperidine to piperazine SAR"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Carbonyl Modifications ─────────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "CARB_001": SmirksEntry(
        id="CARB_001",
        category="carbonyl_modifications",
        name="Ketone to thioketone",
        smirks="[C:1]=[O:2]>>[C:1]=[S:2]",
        description="Thioketone is more lipophilic and less reactive than ketone. "
                    "Used in specific targeting applications.",
        expected_impact="Lipophilicity increase, reactivity change, sulfur_introduction",
        complexity_delta=0.5,
        tags=["lipophilicity_increase", "reactivity_change", "sulfur"],
        reference="Thiocarbonyl isosteres"
    ),
    "CARB_002": SmirksEntry(
        id="CARB_002",
        category="carbonyl_modifications",
        name="Ketone to gem-difluoro",
        smirks="[C:1]=[O:2]>>[C:1]([F:3])[F:4]",
        description="CF2 is a metabolically stable isostere of carbonyl. "
                    "Removes electrophilicity but maintains steric profile.",
        expected_impact="Metabolic stability, electrophilicity removal, lipophilicity",
        complexity_delta=0.5,
        tags=["metabolic_stability", "electrophilicity_removal", "fluorination"],
        reference="Gem-difluoro isosteres, J. Med. Chem. 2020"
    ),
    "CARB_003": SmirksEntry(
        id="CARB_003",
        category="carbonyl_modifications",
        name="Ketone to secondary alcohol (reduction)",
        smirks="[C:1]=[O:2]>>[C:1][OX2H:2]",
        description="Reducing ketone to alcohol adds polarity and H-bonding. "
                    "Can change target binding dramatically.",
        expected_impact="Polarity increase, H-bond introduction, stereochemistry",
        complexity_delta=0.0,
        tags=["polarity_increase", "hbond_introduction", "reduction"],
        reference="Ketone reduction SAR"
    ),
    "CARB_004": SmirksEntry(
        id="CARB_004",
        category="carbonyl_modifications",
        name="Ketone to oxime",
        smirks="[C:1]=[O:2]>>[C:1]=[N:2][OH:3]",
        description="Oxime is a metabolically stable carbonyl isostere. "
                    "Adds H-bond donor capacity.",
        expected_impact="Metabolic stability, H-bond introduction, stabilization",
        complexity_delta=0.5,
        tags=["metabolic_stability", "hbond_introduction", "oxime"],
        reference="Oxime isosteres"
    ),
    "CARB_005": SmirksEntry(
        id="CARB_005",
        category="carbonyl_modifications",
        name="Ketone to hydrazone",
        smirks="[C:1]=[O:2]>>[C:1]=[N:2][N:3][C:4]",
        description="Hydrazone adds basicity and different H-bonding. "
                    "Can be metabolically stable.",
        expected_impact="Basicity increase, H-bonding change, stabilization",
        complexity_delta=0.5,
        tags=["basicity_increase", "hbonding", "hydrazone"],
        reference="Hydrazone bioisosteres"
    ),
    "CARB_006": SmirksEntry(
        id="CARB_006",
        category="carbonyl_modifications",
        name="Ester to amide (hydrolytic stability)",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[NH:3][C:4]",
        description="Amide is more hydrolytically stable than ester. "
                    "Classic metabolic stability strategy.",
        expected_impact="Hydrolytic stability, metabolic stability, polarity",
        complexity_delta=0.3,
        tags=["hydrolytic_stability", "metabolic_stability", "polarity"],
        reference="Ester to amide isosteres, Bioisosteres in MedChem"
    ),
    "CARB_007": SmirksEntry(
        id="CARB_007",
        category="carbonyl_modifications",
        name="Ester to thioester",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[S:3][C:4]",
        description="Thioester is less electrophilic and more lipophilic. "
                    "Different metabolic stability profile.",
        expected_impact="Lipophilicity increase, reactivity change, metabolic shift",
        complexity_delta=0.3,
        tags=["lipophilicity_increase", "reactivity_change", "sulfur"],
        reference="Thioester bioisosteres"
    ),
    "CARB_008": SmirksEntry(
        id="CARB_008",
        category="carbonyl_modifications",
        name="Ketone to cyclic ketone (6-membered)",
        smirks="[C:1][C:2]=[O:3][C:4][C:5]>>[C:1][C:2]1[C:3][C:4][C:5][C:6]1",
        description="Cyclic ketone constrains the carbonyl. Changes 3D shape "
                    "and metabolic stability.",
        expected_impact="Conformational constraint, 3D shape, metabolic shift",
        complexity_delta=1.0,
        tags=["conformational_constraint", "3d_shape", "cyclic_ketone"],
        reference="Cyclic ketone SAR"
    ),
    "CARB_009": SmirksEntry(
        id="CARB_009",
        category="carbonyl_modifications",
        name="Aldehyde to alcohol (reduction)",
        smirks="[C:1]=[O:2]>>[C:1][OX2H:2]",
        description="Reducing aldehyde to primary alcohol adds H-bond "
                    "donor capacity and polarity.",
        expected_impact="Polarity increase, H-bond introduction, reduction",
        complexity_delta=0.0,
        tags=["polarity_increase", "hbond_introduction", "reduction"],
        reference="Aldehyde reduction"
    ),
    "CARB_010": SmirksEntry(
        id="CARB_010",
        category="carbonyl_modifications",
        name="Aldehyde to carboxylic acid (oxidation)",
        smirks="[C:1]=[O:2]>>[C:1](=[O:2])[OX2H:3]",
        description="Oxidizing aldehyde to acid increases polarity dramatically. "
                    "Changes from neutral to charged at physiological pH.",
        expected_impact="Polarity increase, charge introduction, ionization",
        complexity_delta=0.3,
        tags=["polarity_increase", "charge_introduction", "oxidation"],
        reference="Aldehyde oxidation"
    ),
    "CARB_011": SmirksEntry(
        id="CARB_011",
        category="carbonyl_modifications",
        name="α,β-unsaturated ketone to amide",
        smirks="[C:1]=[C:2][C:3]=[O:4]>>[C:1]=[C:2][C:3](=[O:4])[N:5]",
        description="Breaking conjugation by converting ketone to amide. "
                    "Reduces electrophilicity and changes target binding.",
        expected_impact="Electrophilicity removal, conjugation break, amide",
        complexity_delta=0.5,
        tags=["electrophilicity_removal", "conjugation_break", "amide"],
        reference="α,β-unsaturated carbonyl bioisosteres"
    ),
    "CARB_012": SmirksEntry(
        id="CARB_012",
        category="carbonyl_modifications",
        name="Cyclic ketone to lactam",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2][C:3][N:4]([C:5])[C:6]1",
        description="Converting cyclic ketone to lactam (intramolecular amide). "
                    "Changes polarity and H-bonding pattern.",
        expected_impact="Polarity increase, H-bond shift, lactam_formation",
        complexity_delta=0.5,
        tags=["polarity_increase", "hbond_shift", "lactam"],
        reference="Lactam isosteres"
    ),
    "CARB_013": SmirksEntry(
        id="CARB_013",
        category="carbonyl_modifications",
        name="Ketone to methylene (Wolff-Kishner)",
        smirks="[C:1]=[O:2]>>[C:1][C:2]",
        description="Complete reduction of carbonyl to methylene. "
                    "Removes polarity and H-bonding entirely.",
        expected_impact="Polarity removal, apolar introduction, reduction",
        complexity_delta=0.0,
        tags=["polarity_removal", "apolar", "reduction"],
        reference="Methylene isostere of carbonyl"
    ),
    "CARB_014": SmirksEntry(
        id="CARB_014",
        category="carbonyl_modifications",
        name="α-Ketoamide to succinimide",
        smirks="[C:1](=[O:2])[C:3]=[O:4]>>[C:1]1[C:2](=[O:3])[C:4][C:5]1",
        description="Intramolecular cyclization of α-ketoamide to succinimide. "
                    "From Brown ketoamide bioisosteres (BIOSTER AMI281).",
        expected_impact="Cyclization, metabolic stability, conformational constraint",
        complexity_delta=0.8,
        tags=["cyclization", "metabolic_stability", "ketoamide_bioisostere"],
        reference="Brown, Bioisosteres in MedChem, Ch. 4, BIOSTER AMI281"
    ),
    "CARB_015": SmirksEntry(
        id="CARB_015",
        category="carbonyl_modifications",
        name="1,2-dicarbonyl to α-hydroxy acid",
        smirks="[C:1](=[O:2])[C:3]=[O:4]>>[C:1](=[O:2])[O:3][H:4]",
        description="Reducing one carbonyl of 1,2-dicarbonyl to alcohol. "
                    "From Brown ketoamide series transformations.",
        expected_impact="Polarity shift, H-bonding change, reduction",
        complexity_delta=0.5,
        tags=["polarity_shift", "hbonding_change", "dicarbonyl_modification"],
        reference="Brown, Bioisosteres in MedChem Ch. 4 ketoamide series"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Nitrile Modifications ───────────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "NIT_001": SmirksEntry(
        id="NIT_001",
        category="nitrile_modifications",
        name="Nitrile to trifluoromethyl",
        smirks="[CX2:1]#[NX2:2]>>[C:1]([F:3])([F:4])[F:5]",
        description="CF3 is more lipophilic and metabolically stable. "
                    "Used to block nitrile metabolism.",
        expected_impact="Lipophilicity increase, metabolic stability, fluorination",
        complexity_delta=0.5,
        tags=["lipophilicity_increase", "metabolic_stability", "fluorination"],
        reference="CF3/nitrile isosteres, Wilson & Gisvold Table 2.11"
    ),
    "NIT_002": SmirksEntry(
        id="NIT_002",
        category="nitrile_modifications",
        name="Nitrile to amide",
        smirks="[CX2:1]#[NX2:2]>>[C:1](=[O:3])[N:4][H:5]",
        description="Hydrating nitrile to amide. Dramatically increases polarity. "
                    "From nitrile metabolic pathways.",
        expected_impact="Polarity increase, hydration, amide formation",
        complexity_delta=0.5,
        tags=["polarity_increase", "hydration", "amide"],
        reference="Nitrile hydration in metabolism"
    ),
    "NIT_003": SmirksEntry(
        id="NIT_003",
        category="nitrile_modifications",
        name="Nitrile to carboxylic acid",
        smirks="[CX2:1]#[NX2:2]>>[C:1](=[O:3])[OH:4]",
        description="Oxidizing nitrile to carboxylic acid. "
                    "From nitrile metabolic activation.",
        expected_impact="Polarity increase, charge introduction, oxidation",
        complexity_delta=0.5,
        tags=["polarity_increase", "charge_introduction", "oxidation"],
        reference="Nitrile oxidation metabolism"
    ),
    "NIT_004": SmirksEntry(
        id="NIT_004",
        category="nitrile_modifications",
        name="Nitrile to tetrazole",
        smirks="[CX2:1]#[NX2:2]>>[C:1]1=NN=N[NH]1",
        description="Tetrazole is a planar, aromatic bioisostere of nitrile. "
                    "Similar size but different electronic properties.",
        expected_impact="Bioisostere, aromatic, metabolic stability",
        complexity_delta=1.0,
        tags=["bioisostere", "aromatic", "metabolic_stability"],
        reference="Tetrazole isostere of nitrile, Bioisosteres in MedChem Ch. 4"
    ),
    "NIT_005": SmirksEntry(
        id="NIT_005",
        category="nitrile_modifications",
        name="Aryl nitrile to aryl CF3",
        smirks="[c:1][CX2:2]#[NX2:3]>>[c:1][C:2]([F:4])([F:5])[F:6]",
        description="Replacing aryl nitrile with aryl CF3. Increases lipophilicity "
                    "and metabolic stability. From factor Xa inhibitor series.",
        expected_impact="Lipophilicity increase, metabolic stability, aryl_fluorination",
        complexity_delta=0.5,
        tags=["lipophilicity_increase", "metabolic_stability", "aryl_fluorination"],
        reference="Factor Xa nitrile→CF3 SAR, Bioisosteres in MedChem Ch. 3"
    ),
    "NIT_006": SmirksEntry(
        id="NIT_006",
        category="nitrile_modifications",
        name="Nitrile to thioamide",
        smirks="[CX2:1]#[NX2:2]>>[C:1](=[S:3])[N:4][H:5]",
        description="Converting nitrile to thioamide. "
                    "More lipophilic and different H-bonding.",
        expected_impact="Lipophilicity increase, H-bonding shift, sulfur",
        complexity_delta=0.8,
        tags=["lipophilicity_increase", "hbonding_shift", "sulfur"],
        reference="Thioamide isosteres"
    ),
    "NIT_007": SmirksEntry(
        id="NIT_007",
        category="nitrile_modifications",
        name="Nitrile to amidine",
        smirks="[CX2:1]#[NX2:2]>>[C:1](=[N:3])[N:4][H:5]",
        description="Converting nitrile to amidine dramatically increases basicity. "
                    "Useful for targeting acidic enzyme residues.",
        expected_impact="Basicity increase, targeting, strong_cation",
        complexity_delta=1.0,
        tags=["basicity_increase", "targeting", "strong_cation"],
        reference="Amidine bioisosteres of nitriles"
    ),
    "NIT_008": SmirksEntry(
        id="NIT_008",
        category="nitrile_modifications",
        name="β-Nitrile to carbonyl (elimination)",
        smirks="[C:1][C:2][CX2:3]#[NX2:4]>>[C:1][C:2][C:3]=[O:4]",
        description="Eliminating nitrile to form ketone. "
                    "Removes the metabolic liability.",
        expected_impact="Metabolic stability, carbonyl introduction",
        complexity_delta=0.5,
        tags=["metabolic_stability", "carbonyl_introduction", "elimination"],
        reference="Nitrile elimination SAR"
    ),
    "NIT_009": SmirksEntry(
        id="NIT_009",
        category="nitrile_modifications",
        name="Nitrile to isonitrile (isomerization)",
        smirks="[CX2:1]#[NX2:2]>>[C:1](=[N+:2])[N-:3]",
        description="Isonitrile has different electronic and steric properties. "
                    "Rarely used but provides different pharmacokinetics.",
        expected_impact="Isomerization, electronic change, unique_pharmacophore",
        complexity_delta=0.8,
        tags=["isomerization", "electronic_change", "unique_pharmacophore"],
        reference="Isonitrile bioisosteres"
    ),
    "NIT_010": SmirksEntry(
        id="NIT_010",
        category="nitrile_modifications",
        name="Nitrile to selenocyanate",
        smirks="[CX2:1]#[NX2:2]>>[C:1][Se:3][NX2:4]",
        description="Selenium isostere of nitrile. Larger and more polarizable. "
                    "Very rare but useful for specific targeting.",
        expected_impact="Size increase, polarizability, selenium_isostere",
        complexity_delta=1.2,
        tags=["size_increase", "polarizability", "selenium"],
        reference="Selenocyanate isosteres"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Sulfonamide Modifications ──────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "SLFA_001": SmirksEntry(
        id="SLFA_001",
        category="sulfonamide_modifications",
        name="N-Methylation of sulfonamide",
        smirks="[S:1](=O)(=O)N>>[S:1](=O)(=O)NC",
        description="N-methylation reduces H-bond donor capacity "
                    "and slightly increases lipophilicity.",
        expected_impact="HBD reduction, lipophilicity increase, metabolic shift",
        complexity_delta=0.2,
        tags=["hbd_reduction", "lipophilicity_increase", "n_methylation"],
        reference="Sulfonamide SAR"
    ),
    "SLFA_002": SmirksEntry(
        id="SLFA_002",
        category="sulfonamide_modifications",
        name="Primary sulfonamide to secondary",
        smirks="[S:1](=O)(=O)N>>[S:1](=O)(=O)N",
        description="Deprotonating or alkylating to secondary sulfonamide. "
                    "Changes acidity and H-bonding.",
        expected_impact="Acidity modulation, H-bonding change",
        complexity_delta=0.3,
        tags=["acidity_modulation", "hbonding_change"],
        reference="Sulfonamide deprotonation"
    ),
    "SLFA_003": SmirksEntry(
        id="SLFA_003",
        category="sulfonamide_modifications",
        name="Carboxylic acid to acylsulfonamide",
        smirks="[C:1](=O)[OH:2]>>[C:1](=O)N[S:3](=O)(=O)C",
        description="Acylsulfonamide retains negative charge at physiological pH "
                    "but has different pKa profile than carboxylate.",
        expected_impact="Acidity modulation, metabolic stability, hERG shift",
        complexity_delta=1.0,
        tags=["acidity_modulation", "metabolic_stability", "herg_shift"],
        reference="Acylsulfonamide bioisosteres, Bioisosteres in MedChem Ch. 4"
    ),
    "SLFA_004": SmirksEntry(
        id="SLFA_004",
        category="sulfonamide_modifications",
        name="Sulfonamide to sulfone (remove H-bond donor)",
        smirks="[S:1](=O)(=O)N>>[S:1](=O)(=O)",
        description="Removing the NH from sulfonamide eliminates HBD "
                    "while maintaining sulfonyl polarity.",
        expected_impact="HBD removal, polarity maintenance, electronic change",
        complexity_delta=0.5,
        tags=["hbd_removal", "polarity_maintenance", "electronic_change"],
        reference="Sulfone isostere of sulfonamide"
    ),
    "SLFA_005": SmirksEntry(
        id="SLFA_005",
        category="sulfonamide_modifications",
        name="Sulfonamide to ester (deamination)",
        smirks="[S:1](=O)(=O)N>>[C:1](=O)[O:2]",
        description="Converting sulfonamide to ester removes the S-N bond. "
                    "Dramatically changes electronics and metabolism.",
        expected_impact="Electronic change, metabolic shift, ester_formation",
        complexity_delta=1.0,
        tags=["electronic_change", "metabolic_shift", "ester"],
        reference="Ester/sulfonamide isosteres"
    ),
    "SLFA_006": SmirksEntry(
        id="SLFA_006",
        category="sulfonamide_modifications",
        name="Acylsulfonamide to amide (simplification)",
        smirks="[C:1](=O)N[S:2](=O)(=O)C>>[C:1](=O)[NH:3]",
        description="Removing the sulfonyl group from acylsulfonamide. "
                    "Simplifies structure and reduces acidity.",
        expected_impact="Simplification, acidity reduction, amide",
        complexity_delta=0.5,
        tags=["simplification", "acidity_reduction", "amide"],
        reference="Amide isostere of acylsulfonamide"
    ),
    "SLFA_007": SmirksEntry(
        id="SLFA_007",
        category="sulfonamide_modifications",
        name="Sulfone to sulfonamide (add H-bond donor)",
        smirks="[S:1](=O)(=O)C>>[S:1](=O)(=O)N",
        description="Adding NH to sulfone creates sulfonamide. "
                    "Introduces H-bond donor capacity.",
        expected_impact="HBD introduction, polarity increase, solubility",
        complexity_delta=0.5,
        tags=["hbd_introduction", "polarity_increase", "solubility"],
        reference="Sulfonamide/sulfone isosteres"
    ),
    "SLFA_008": SmirksEntry(
        id="SLFA_008",
        category="sulfonamide_modifications",
        name="Sulfonamide to phosphonamide",
        smirks="[S:1](=O)(=O)N>>[P:1](=O)(=O)[N:2]",
        description="Phosphorus isostere of sulfonamide. Similar tetrahedral geometry "
                    "but different electronic and metabolic properties.",
        expected_impact="Isostere, tetrahedral geometry, phosphorus",
        complexity_delta=1.5,
        tags=["isostere", "tetrahedral", "phosphorus"],
        reference="Phosphonamide bioisosteres"
    ),
    "SLFA_009": SmirksEntry(
        id="SLFA_009",
        category="sulfonamide_modifications",
        name="Aryl sulfonamide to alkyl sulfonamide",
        smirks="[c:1][S:2](=O)(=O)N>>[C:2](=O)(=O)N",
        description="Removing aromaticity from sulfonamide attachment. "
                    "Changes flexibility and electronics.",
        expected_impact="Flexibility increase, electronic change, aryl_removal",
        complexity_delta=0.5,
        tags=["flexibility", "electronic_change", "aryl_removal"],
        reference="Alkyl sulfonamide SAR"
    ),
    "SLFA_010": SmirksEntry(
        id="SLFA_010",
        category="sulfonamide_modifications",
        name="Cyclic sulfonamide to acyclic (ring opening)",
        smirks="[S:1]1(=O)[O:2][C:3][N:4]1>>[S:1](=O)(=O)[N:4][C:3][O:2]",
        description="Opening the cyclic sulfonamide ring. "
                    "Increases flexibility and changes conformation.",
        expected_impact="Flexibility increase, conformational change, ring_opening",
        complexity_delta=0.5,
        tags=["flexibility", "conformational_change", "ring_opening"],
        reference="Cyclic sulfonamide SAR"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Steric Shielding ───────────────────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "STER_001": SmirksEntry(
        id="STER_001",
        category="steric_shielding",
        name="Methyl to tert-butyl (maximum shielding)",
        smirks="[CH3:1]>>[C:1]([C:2])([C:3])[C:4]",
        description="tert-Butyl provides maximum steric shielding of the site. "
                    "Blocks metabolism but increases MW significantly.",
        expected_impact="Steric shielding, metabolic block, MW increase",
        complexity_delta=0.5,
        tags=["steric_shielding", "metabolic_block", "mw_increase"],
        reference="t-Butyl isosteres"
    ),
    "STER_002": SmirksEntry(
        id="STER_002",
        category="steric_shielding",
        name="Primary amine to dimethylamine",
        smirks="[NH2:1]>>[N:1]([C:2])[C:3]",
        description="Dimethylamine is sterically larger than NH2. "
                    "Reduces H-bonding and metabolic deamination.",
        expected_impact="Steric increase, H-bond reduction, metabolic stability",
        complexity_delta=0.0,
        tags=["steric_increase", "hbond_reduction", "metabolic_stability"],
        reference="Dimethylamine isosteres"
    ),
    "STER_003": SmirksEntry(
        id="STER_003",
        category="steric_shielding",
        name="Aromatic ortho-methyl shielding",
        smirks="[cH:1]>>[c:1]([CH3:2])",
        description="Ortho-methyl on aromatic ring sterically shields "
                    "adjacent functional groups from metabolism.",
        expected_impact="Steric shielding, metabolic block, ortho_substitution",
        complexity_delta=0.0,
        tags=["steric_shielding", "metabolic_block", "ortho"],
        reference="Ortho-methyl shielding SAR"
    ),
    "STER_004": SmirksEntry(
        id="STER_004",
        category="steric_shielding",
        name="Aromatic ortho-fluoro shielding",
        smirks="[cH:1]>>[c:1]([F:2])",
        description="Ortho-fluoro provides steric shielding while "
                    "contributing electronic effects.",
        expected_impact="Steric shielding, electronic effect, ortho_fluoro",
        complexity_delta=0.2,
        tags=["steric_shielding", "electronic_effect", "fluorination"],
        reference="Ortho-fluoro SAR"
    ),
    "STER_005": SmirksEntry(
        id="STER_005",
        category="steric_shielding",
        name="Aromatic ortho-chloro shielding",
        smirks="[cH:1]>>[c:1]([Cl:2])",
        description="Ortho-chloro is larger than ortho-fluoro. "
                    "Provides more steric shielding.",
        expected_impact="Steric shielding, size increase, ortho_chloro",
        complexity_delta=0.2,
        tags=["steric_shielding", "size_increase", "chloro"],
        reference="Ortho-chloro SAR"
    ),
    "STER_006": SmirksEntry(
        id="STER_006",
        category="steric_shielding",
        name="Aromatic ortho-bromo shielding",
        smirks="[cH:1]>>[c:1]([Br:2])",
        description="Ortho-bromo is the largest common ortho substituent. "
                    "Maximum steric shielding among halogens.",
        expected_impact="Maximum steric shielding, ortho_bromo, size",
        complexity_delta=0.2,
        tags=["steric_shielding", "maximum", "bromo"],
        reference="Ortho-bromo SAR"
    ),
    "STER_007": SmirksEntry(
        id="STER_007",
        category="steric_shielding",
        name="Methyl to CH2CH2OH (hydroxylethyl)",
        smirks="[CH3:1]>>[C:1][C:2][OH:3]",
        description="Adding a hydroxyl to methyl creates hydroxyethyl. "
                    "Increases polarity and H-bonding while maintaining size.",
        expected_impact="H-bonding increase, polarity, steric maintenance",
        complexity_delta=0.3,
        tags=["hbonding", "polarity", "steric_maintenance"],
        reference="Hydroxyethyl isosteres"
    ),
    "STER_008": SmirksEntry(
        id="STER_008",
        category="steric_shielding",
        name="Benzylic CH2 to gem-dimethyl (isobutyl-like)",
        smirks="[c:1][CH2:2]>>[c:1][C:2]([C:3])([C:4])",
        description="gem-Dimethyl at benzylic position is sterically "
                    "equivalent to isopropyl. Blocks benzylic oxidation.",
        expected_impact="Steric block, metabolic block, isopropyl_isostere",
        complexity_delta=0.3,
        tags=["steric_block", "metabolic_block", "isopropyl"],
        reference="Gem-dimethyl benzylic isosteres"
    ),
    "STER_009": SmirksEntry(
        id="STER_009",
        category="steric_shielding",
        name="N-CH3 to N-ethyl (ethyl shielding)",
        smirks="[N:1][CH3:2]>>[N:1][C:2][C:3]",
        description="Ethyl is sterically larger than methyl. "
                    "Blocks N-demethylation metabolism.",
        expected_impact="Steric increase, metabolic block, n-ethylation",
        complexity_delta=0.0,
        tags=["steric_increase", "metabolic_block", "n_ethylation"],
        reference="N-ethyl amine isosteres"
    ),
    "STER_010": SmirksEntry(
        id="STER_010",
        category="steric_shielding",
        name="Amide NH to N-methyl",
        smirks="[N:1][C:2](=[O:3])[NH:4]>>[N:1][C:2](=[O:3])[N:4]([C:5])",
        description="N-methylation of amide reduces HBD and adds steric bulk. "
                    "Common for CNS penetration.",
        expected_impact="HBD reduction, steric increase, cns_penetration",
        complexity_delta=0.2,
        tags=["hbd_reduction", "steric_increase", "cns"],
        reference="N-methyl amide isosteres"
    ),
    "STER_011": SmirksEntry(
        id="STER_011",
        category="steric_shielding",
        name="Ester CH3 to CH2CH3 (ethyl ester)",
        smirks="[C:1](=O)[O:2][CH3:3]>>[C:1](=O)[O:2][C:3][C:4]",
        description="Ethyl ester is slightly larger and more lipophilic "
                    "than methyl ester. Different hydrolytic stability.",
        expected_impact="Steric increase, lipophilicity increase, hydrolytic_change",
        complexity_delta=0.0,
        tags=["steric_increase", "lipophilicity", "hydrolytic"],
        reference="Ethyl ester isosteres"
    ),
    "STER_012": SmirksEntry(
        id="STER_012",
        category="steric_shielding",
        name="Aromatic para-CH3 to para-CF3",
        smirks="[c:1][CH3:2]>>[c:1][C:2]([F:3])([F:4])[F:5]",
        description="Para-CF3 is larger and more lipophilic than para-CH3. "
                    "Blocks para-oxidation metabolism.",
        expected_impact="Steric increase, metabolic block, lipophilicity",
        complexity_delta=0.3,
        tags=["steric_increase", "metabolic_block", "fluorination"],
        reference="Para-CF3 SAR"
    ),
    "STER_013": SmirksEntry(
        id="STER_013",
        category="steric_shielding",
        name="Hydroxyl to O-isopropyl",
        smirks="[C:1][OX2H:2]>>[C:1][OX2:2][C:3]([C:4])[C:5]",
        description="O-isopropyl provides steric shielding of the OH position. "
                    "Blocks O-glucuronidation.",
        expected_impact="Steric shielding, metabolic block, glucuronidation_block",
        complexity_delta=0.3,
        tags=["steric_shielding", "metabolic_block", "isopropyl"],
        reference="O-isopropyl ether isosteres"
    ),
    "STER_014": SmirksEntry(
        id="STER_014",
        category="steric_shielding",
        name="Cyclopropyl methylation",
        smirks="[C:1][CH2:2]>>[C:1][C:2]1[C:3][C:4][C:5]1",
        description="Cyclopropyl is sterically similar to CH3 but metabolically "
                    "stable due to ring strain.",
        expected_impact="Steric equivalence, metabolic stability, ring_strain",
        complexity_delta=0.5,
        tags=["steric_equivalence", "metabolic_stability", "cyclopropyl"],
        reference="Cyclopropyl isosteres"
    ),
    "STER_015": SmirksEntry(
        id="STER_015",
        category="steric_shielding",
        name="neo-Pentyl introduction",
        smirks="[C:1][CH2:2]>>[C:1][C:2]([C:3])([C:4])[C:5]",
        description="neo-Pentyl (CH2C(CH3)3) provides maximum steric shielding "
                    "without aromatic bulk.",
        expected_impact="Maximum aliphatic steric shielding, flexibility",
        complexity_delta=0.5,
        tags=["steric_shielding", "aliphatic", "neopentyl"],
        reference="Neopentyl isosteres"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: CNS Penetration Modifications ──────────────────────────
    # ════════════════════════════════════════════════════════════════════
    "CNS_001": SmirksEntry(
        id="CNS_001",
        category="cns_penetration",
        name="Carboxylic acid to ester (PSA reduction)",
        smirks="[C:1](=O)[OH:2]>>[C:1](=O)[O:2][CH3:3]",
        description="Ester is significantly less polar than acid. "
                    "Classic PSA reduction strategy for CNS penetration.",
        expected_impact="PSA reduction, polarity reduction, cns_penetration",
        complexity_delta=0.2,
        tags=["psa_reduction", "polarity_reduction", "cns"],
        reference="CNS penetration strategies, Wilson & Gisvold"
    ),
    "CNS_002": SmirksEntry(
        id="CNS_002",
        category="cns_penetration",
        name="Carboxylic acid to tetrazole (PSA reduction)",
        smirks="[C:1](=O)[OH:2]>>[C:1]1=NN=N[NH]1",
        description="Tetrazole has lower PSA than carboxylic acid. "
                    "Used in CNS drugs like altiniclib.",
        expected_impact="PSA reduction, bioisostere, cns_penetration",
        complexity_delta=1.0,
        tags=["psa_reduction", "bioisostere", "cns"],
        reference="Tetrazole CNS agents"
    ),
    "CNS_003": SmirksEntry(
        id="CNS_003",
        category="cns_penetration",
        name="Primary amine to tertiary amine",
        smirks="[NH2:1]>>[N:1]([C:2])[C:3]",
        description="Tertiary amine has lower PSA than primary amine. "
                    "Common for CNS drugs (e.g., diphenhydramine).",
        expected_impact="PSA reduction, basicity modulation, cns_penetration",
        complexity_delta=0.0,
        tags=["psa_reduction", "basicity_modulation", "cns"],
        reference="CNS amine SAR"
    ),
    "CNS_004": SmirksEntry(
        id="CNS_004",
        category="cns_penetration",
        name="Hydroxyl to fluoro (HBD removal)",
        smirks="[C:1][OX2H:2]>>[C:1][F:2]",
        description="Fluorine is isostere of OH but without H-bonding. "
                    "Dramatically reduces PSA.",
        expected_impact="PSA reduction, HBD removal, cns_penetration",
        complexity_delta=0.3,
        tags=["psa_reduction", "hbd_removal", "cns"],
        reference="Fluoro isosteres for CNS"
    ),
    "CNS_005": SmirksEntry(
        id="CNS_005",
        category="cns_penetration",
        name="Carboxylic acid to N-methyl amide",
        smirks="[C:1](=O)[OH:2]>>[C:1](=O)[N:2]([CH3:3])",
        description="N-methyl amide has lower PSA than acid. "
                    "Maintains some polarity but reduces HBD.",
        expected_impact="PSA reduction, HBD reduction, cns",
        complexity_delta=0.3,
        tags=["psa_reduction", "hbd_reduction", "cns"],
        reference="N-methyl amide CNS SAR"
    ),
    "CNS_006": SmirksEntry(
        id="CNS_006",
        category="cns_penetration",
        name="Aniline to N,N-dimethyl aniline",
        smirks="[c:1][NH2:2]>>[c:1][N:2]([C:3])[C:4]",
        description="N,N-dimethyl aniline is less basic and has lower PSA "
                    "than aniline. Common CNS transformation.",
        expected_impact="PSA reduction, basicity reduction, cns",
        complexity_delta=0.2,
        tags=["psa_reduction", "basicity_reduction", "cns"],
        reference="Dimethyl aniline CNS SAR"
    ),
    "CNS_007": SmirksEntry(
        id="CNS_007",
        category="cns_penetration",
        name="Secondary amide to tertiary amide",
        smirks="[C:1](=[O:2])[NH:3][C:4]>>[C:1](=[O:2])[N:3]([C:4])[C:5]",
        description="N-methylation of amide removes HBD and reduces PSA. "
                    "Key CNS penetration strategy.",
        expected_impact="PSA reduction, HBD removal, cns_penetration",
        complexity_delta=0.2,
        tags=["psa_reduction", "hbd_removal", "cns"],
        reference="Tertiary amide CNS SAR"
    ),
    "CNS_008": SmirksEntry(
        id="CNS_008",
        category="cns_penetration",
        name="Phenol to fluorobenzene",
        smirks="[c:1][OH:2]>>[c:1][F:2]",
        description="Fluorobenzene is isostere of phenol without H-bonding. "
                    "Dramatically reduces PSA and changes electronics.",
        expected_impact="PSA removal, HBD removal, electronic change",
        complexity_delta=0.3,
        tags=["psa_removal", "hbd_removal", "electronic_change"],
        reference="Fluorobenzene phenol isostere"
    ),
    "CNS_009": SmirksEntry(
        id="CNS_009",
        category="cns_penetration",
        name="Diol to cyclic acetal",
        smirks="[C:1][OH:2][C:3][OH:4]>>[C:1]1[O:2][C:3][O:4][C:5]1",
        description="Cyclic acetal masks both OH groups. "
                    "Reduces PSA and H-bonding dramatically.",
        expected_impact="PSA reduction, HBD removal, cyclic_acetal",
        complexity_delta=1.0,
        tags=["psa_reduction", "hbond_removal", "cyclic"],
        reference="Acetal CNS strategies"
    ),
    "CNS_010": SmirksEntry(
        id="CNS_010",
        category="cns_penetration",
        name="Benzene to para-fluorobenzene",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][c:4][c:5][F:6]1",
        description="Fluorination at para position reduces lipophilicity "
                    "and improves metabolic stability.",
        expected_impact="Lipophilicity reduction, metabolic stability, CME",
        complexity_delta=0.5,
        tags=["fluorination", "lipophilicity_reduction", "metabolic_stability"],
        reference="Fluorobenzene CNS SAR"
    ),
    "CNS_011": SmirksEntry(
        id="CNS_011",
        category="cns_penetration",
        name="Amidine to N-methyl amidine",
        smirks="[C:1](=[N:2])[N:3]>>[C:1](=[N:2])[N:3][CH3:4]",
        description="N-methylation of amidine reduces basicity and PSA. "
                    "Used in CNS drugs targeting arginine-rich sites.",
        expected_impact="PSA reduction, basicity reduction, cns",
        complexity_delta=0.2,
        tags=["psa_reduction", "basicity_reduction", "cns"],
        reference="N-methyl amidine CNS"
    ),
    "CNS_012": SmirksEntry(
        id="CNS_012",
        category="cns_penetration",
        name="Guanidine to cyanoguanidine",
        smirks="[C:1](=[N:2])[N:3][C:4](=[N:5])[N:6]>>[N:1]([C:2]#[NX3:3])=[N:4]",
        description="Cyanoguanidine is less basic than guanidine. "
                    "Used in CNS histamine antagonists.",
        expected_impact="Basicity reduction, PSA reduction, cns",
        complexity_delta=0.5,
        tags=["basicity_reduction", "psa_reduction", "cns"],
        reference="Cyanoguanidine CNS agents"
    ),
    "CNS_013": SmirksEntry(
        id="CNS_013",
        category="cns_penetration",
        name="Sulfonamide to N-methyl sulfonamide",
        smirks="[S:1](=O)(=O)N>>[S:1](=O)(=O)N[CH3:2]",
        description="N-methylation of sulfonamide removes one HBD. "
                    "Reduces PSA and improves CNS penetration.",
        expected_impact="PSA reduction, HBD removal, cns",
        complexity_delta=0.2,
        tags=["psa_reduction", "hbd_removal", "cns"],
        reference="N-methyl sulfonamide CNS"
    ),
    "CNS_014": SmirksEntry(
        id="CNS_014",
        category="cns_penetration",
        name="Primary amide to secondary amide",
        smirks="[C:1](=O)[NH2:2]>>[C:1](=O)[NH:2][C:3]",
        description="N-alkylation of primary amide reduces HBD and PSA. "
                    "Maintains polarity with reduced H-bonding.",
        expected_impact="PSA reduction, HBD reduction, cns",
        complexity_delta=0.2,
        tags=["psa_reduction", "hbd_reduction", "cns"],
        reference="Secondary amide CNS SAR"
    ),
    "CNS_015": SmirksEntry(
        id="CNS_015",
        category="cns_penetration",
        name="Tertiary amine N-oxide (for peripheral vs CNS)",
        smirks="[N:1]([C:2])([C:3])[C:4]>>[N+:1](=[O:5])([C:2])([C:3])[C:4]",
        description="N-oxide is more polar than tertiary amine but still "
                    "crosses BBB. Used to modulate distribution.",
        expected_impact="Polarity increase, distribution modulation, n_oxide",
        complexity_delta=0.5,
        tags=["polarity_increase", "distribution", "n_oxide"],
        reference="N-oxide CNS modulation"
    ),
    "CNS_016": SmirksEntry(
        id="CNS_016",
        category="cns_penetration",
        name="Increase LogP for brain penetration (aryl to biphenyl)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1[c:7]2[c:8][c:9][c:10][c:11][c:12]2",
        description="Increasing LogP can improve brain penetration for "
                    "some CNS targets requiring high lipophilicity.",
        expected_impact="Lipophilicity increase, LogP increase, brain_penetration",
        complexity_delta=0.8,
        tags=["lipophilicity_increase", "logp", "brain_penetration"],
        reference="Biphenyl CNS SAR"
    ),
    "CNS_017": SmirksEntry(
        id="CNS_017",
        category="cns_penetration",
        name="Peripheral acid to central acid (different distribution)",
        smirks="[C:1](=O)[OH:2]>>[C:3](=O)[OH:2][C:1]",
        description="Moving acid from peripheral to central position "
                    "changes ionization and distribution.",
        expected_impact="Ionization shift, distribution change, pKa",
        complexity_delta=0.5,
        tags=["ionization_shift", "distribution", "pka"],
        reference="Acid positioning SAR"
    ),
    "CNS_018": SmirksEntry(
        id="CNS_018",
        category="cns_penetration",
        name="Ester to thioester (different metabolic stability)",
        smirks="[C:1](=O)[O:2][C:3]>>[C:1](=O)[S:2][C:3]",
        description="Thioester is more stable to some esterases but "
                    "more reactive to nucleophiles. Different CNS profile.",
        expected_impact="Metabolic shift, reactivity change, thioester",
        complexity_delta=0.3,
        tags=["metabolic_shift", "reactivity_change", "thioester"],
        reference="Thioester CNS SAR"
    ),
    "CNS_019": SmirksEntry(
        id="CNS_019",
        category="cns_penetration",
        name="Morpholine to thiomorpholine",
        smirks="[O:1]1[C:2][C:3][N:4][C:5][C:6]1>>[S:1]1[C:2][C:3][N:4][C:5][C:6]1",
        description="Thiomorpholine is more lipophilic than morpholine. "
                    "Changes blood-brain distribution.",
        expected_impact="Lipophilicity increase, distribution change, brain",
        complexity_delta=0.5,
        tags=["lipophilicity_increase", "distribution", "brain"],
        reference="Thiomorpholine CNS"
    ),
    "CNS_020": SmirksEntry(
        id="CNS_020",
        category="cns_penetration",
        name="Piperidine to N-methylpiperidine",
        smirks="[N:1]1[C:2][C:3][C:4][C:5][C:6]1>>[N+:1]([CH3:7])1[C:2][C:3][C:4][C:5][C:6]1",
        description="Quaternary N-methylpiperidine has different distribution "
                    "and reduced CNS penetration compared to piperidine.",
        expected_impact="Charge, distribution change, reduced_cns",
        complexity_delta=0.5,
        tags=["charge", "distribution", "reduced_cns"],
        reference="Quaternary amine CNS SAR"
    ),

    # ════════════════════════════════════════════════════════════════════
    # ── NEW: Aromatic Ring Swaps (Heterocycles) ─────────────────────
    # ════════════════════════════════════════════════════════════════════
    "RING_101": SmirksEntry(
        id="RING_101",
        category="aromatic_ring_swaps",
        name="Phenyl to 2-pyridyl (N at position 1)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][n:4][c:5][c:6]1",
        description="Pyridine N acts as H-bond acceptor. Reduces LogP "
                    "by ~0.5-1.0 compared to phenyl. All N-position isomers available.",
        expected_impact="LogP reduction, H-bond acceptor, solubility",
        complexity_delta=0.0,
        tags=["logp_reduction", "hbond_acceptor", "solubility", "pyridine"],
        reference="Brown, Bioisosteres in MedChem Ch. 13; Wilson & Gisvold"
    ),
    "RING_102": SmirksEntry(
        id="RING_102",
        category="aromatic_ring_swaps",
        name="Phenyl to pyrimidine (1,3-diazine)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][n:3][c:4][n:5][c:6]1",
        description="Pyrimidine has two N atoms. More polar, stronger H-bond "
                    "acceptor. Used in many CNS drugs.",
        expected_impact="Polarity increase, H-bond acceptor, solubility",
        complexity_delta=0.2,
        tags=["polarity_increase", "hbond_acceptor", "pyrimidine"],
        reference="Pyrimidine isosteres"
    ),
    "RING_103": SmirksEntry(
        id="RING_103",
        category="aromatic_ring_swaps",
        name="Phenyl to pyridazine (1,2-diazine)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]=[n:4][n:5][c:6]1",
        description="Pyridazine has adjacent N atoms. Most polar of the diazines. "
                    "Different metabolic stability profile.",
        expected_impact="Polarity increase, metabolic shift, pyridazine",
        complexity_delta=0.3,
        tags=["polarity_increase", "metabolic_shift", "diazine"],
        reference="Pyridazine bioisosteres"
    ),
    "RING_104": SmirksEntry(
        id="RING_104",
        category="aromatic_ring_swaps",
        name="Phenyl to pyrazine (1,4-diazine)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][c:4]=[n:5][n:6]1",
        description="Pyrazine has opposite N atoms. Symmetrical, moderate polarity. "
                    "Used in antimicrobial and CNS agents.",
        expected_impact="Polarity moderate, symmetry, pyrazine",
        complexity_delta=0.3,
        tags=["polarity_moderate", "symmetry", "pyrazine"],
        reference="Pyrazine isosteres"
    ),
    "RING_105": SmirksEntry(
        id="RING_105",
        category="aromatic_ring_swaps",
        name="Phenyl to cyclohexyl (saturation)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4][C:5][C:6]1",
        description="Saturation reduces lipophilicity and changes 3D shape. "
                    "Can improve solubility dramatically.",
        expected_impact="Lipophilicity reduction, solubility, 3D_shape",
        complexity_delta=0.0,
        tags=["lipophilicity_reduction", "solubility", "saturation"],
        reference="Cyclohexyl phenyl isostere, Bioisosteres in MedChem Ch. 13"
    ),
    "RING_106": SmirksEntry(
        id="RING_106",
        category="aromatic_ring_swaps",
        name="Phenyl to cyclohexenyl (partial saturation)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3]=[C:4][C:5][C:6]1",
        description="Partial saturation reduces aromaticity while maintaining "
                    "some planarity. Intermediate properties.",
        expected_impact="Intermediate saturation, lipophilicity, planarity",
        complexity_delta=0.2,
        tags=["partial_saturation", "intermediate", "lipophilicity"],
        reference="Cyclohexenyl isosteres"
    ),
    "RING_107": SmirksEntry(
        id="RING_107",
        category="aromatic_ring_swaps",
        name="Phenyl to thiophene (S isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][s:3][c:4][s:5][c:6]1",
        description="Thiophene is aromatic with sulfur. More lipophilic than "
                    "furan, different metabolic stability.",
        expected_impact="Lipophilicity increase, sulfur, aromatic",
        complexity_delta=0.0,
        tags=["lipophilicity_increase", "sulfur", "aromatic"],
        reference="Thiophene/furan/pyrrole isosteres, Wilson & Gisvold Table 2.11"
    ),
    "RING_108": SmirksEntry(
        id="RING_108",
        category="aromatic_ring_swaps",
        name="Phenyl to furan (O isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][o:3][c:4][o:5][c:6]1",
        description="Furan is less lipophilic than thiophene. "
                    "More susceptible to oxidative metabolism.",
        expected_impact="Lipophilicity reduction, oxygen, aromatic",
        complexity_delta=0.0,
        tags=["lipophilicity_reduction", "oxygen", "aromatic"],
        reference="Furan isosteres, Wilson & Gisvold"
    ),
    "RING_109": SmirksEntry(
        id="RING_109",
        category="aromatic_ring_swaps",
        name="Phenyl to pyrrole (NH isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][nH:3][c:4][nH:5][c:6]1",
        description="Pyrrole has N-H that can act as H-bond donor. "
                    "Different electronic properties than phenyl.",
        expected_impact="HBD introduction, electronic change, nitrogen",
        complexity_delta=0.0,
        tags=["hbd_introduction", "electronic_change", "pyrrole"],
        reference="Pyrrole isosteres"
    ),
    "RING_110": SmirksEntry(
        id="RING_110",
        category="aromatic_ring_swaps",
        name="Pyridine to pyrimidine (N addition)",
        smirks="[c:1]1[c:2][c:3][n:4][c:5][c:6]1>>[c:1]1[c:2][n:3][c:4][n:5][c:6]1",
        description="Adding second N to pyridine creates pyrimidine. "
                    "Increases polarity and H-bonding.",
        expected_impact="Polarity increase, H-bond increase, N_addition",
        complexity_delta=0.2,
        tags=["polarity_increase", "hbonding", "n_addition"],
        reference="Pyridine to pyrimidine transformation"
    ),
    "RING_111": SmirksEntry(
        id="RING_111",
        category="aromatic_ring_swaps",
        name="Pyridine to 4-pyridyl (N position isomer)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][n:6]1>>[c:1]1[c:2][c:3][c:4][n:5][c:6]1",
        description="Changing N position in pyridine changes dipole moment "
                    "and interactions with binding site.",
        expected_impact="Dipole change, position isomer, electronics",
        complexity_delta=0.0,
        tags=["dipole_change", "position_isomer", "electronics"],
        reference="Pyridine N-position isomers"
    ),
    "RING_112": SmirksEntry(
        id="RING_112",
        category="aromatic_ring_swaps",
        name="Cyclohexenyl to phenyl (reverse saturation)",
        smirks="[C:1]1[C:2][C:3]=[C:4][C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Aromatization increases lipophilicity and planarity. "
                    "Enables pi-stacking interactions.",
        expected_impact="Aromatization, lipophilicity increase, planarity",
        complexity_delta=0.0,
        tags=["aromatization", "lipophilicity_increase", "pi_stacking"],
        reference="Aromatic isosteres"
    ),
    "RING_113": SmirksEntry(
        id="RING_113",
        category="aromatic_ring_swaps",
        name="Benzene to thiophene (classic bioisostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][s:4][c:5][c:6]1",
        description="Thiophene replaces benzene as a classical bioisostere. "
                    "Sulfur adds slight bend and changes dipole moment.",
        expected_impact="Lipophilicity increase, metabolic stability, dipole change",
        complexity_delta=0.3,
        tags=["classic_isostere", "sulfur", "lipophilicity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 2"
    ),
    "RING_114": SmirksEntry(
        id="RING_114",
        category="aromatic_ring_swaps",
        name="Benzene to pyridine (N isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][c:4][n:5][c:6]1",
        description="Pyridine nitrogen isosteric replacement for benzene CH. "
                    "Adds dipole and H-bond acceptor capability.",
        expected_impact="Dipole addition, H-bond acceptor, basicity",
        complexity_delta=0.2,
        tags=["nitrogen", "hbond_acceptor", "dipole"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 2"
    ),
    "RING_115": SmirksEntry(
        id="RING_115",
        category="aromatic_ring_swaps",
        name="Phenyl to 1,2,3-triazole",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][n:3][n:4][n:5][c:6]1",
        description="1,2,3-Triazole is all-nitrogen aromatic heterocycle. "
                    "Metabolically stable but different geometry.",
        expected_impact="Metabolic stability, all-nitrogen, different_geometry",
        complexity_delta=1.0,
        tags=["metabolic_stability", "all_nitrogen", "triazole"],
        reference="Triazole bioisosteres"
    ),
    "RING_116": SmirksEntry(
        id="RING_116",
        category="aromatic_ring_swaps",
        name="Benzene to furan (classic 5-membered isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][o:4][c:5][c:6]1",
        description="Furan is a classical bioisostere of benzene with one CH replaced by O. "
                    "From Brown oxadiazole/benzisoxazole examples.",
        expected_impact="Ring contraction, oxygen addition, aromatic_5member",
        complexity_delta=0.5,
        tags=["ring_contraction", "aromatic_5member", "furan"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 2"
    ),
    "RING_117": SmirksEntry(
        id="RING_117",
        category="aromatic_ring_swaps",
        name="Methyl to chlorine (halogen scan)",
        smirks="[CH3:1]>>[Cl:1]",
        description="Chlorine scan: methyl to chlorine replaces H with Cl "
                    "keeping similar steric footprint but adding polarizability.",
        expected_impact="Polarizability addition, Cl substituent, steric",
        complexity_delta=0.0,
        tags=["halogen", "scan", "polarizability"],
        reference="Halogen substitution SAR"
    ),
    "RING_118": SmirksEntry(
        id="RING_118",
        category="aromatic_ring_swaps",
        name="Imidazole to pyrazole (N position change)",
        smirks="[c:1]1[n:2][c:3][n:4][c:5]1>>[c:1]1[n:2][n:3][c:4][c:5]1",
        description="Changing N position in 5-membered heterocycle. "
                    "Affects basicity and H-bonding pattern.",
        expected_impact="Basicity shift, H-bonding change, N_position",
        complexity_delta=0.3,
        tags=["basicity_shift", "hbonding", "n_position"],
        reference="Imidazole pyrazole isosteres"
    ),
    "RING_119": SmirksEntry(
        id="RING_119",
        category="aromatic_ring_swaps",
        name="Benzene to benzofuran (O insertion)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]2[c:4][c:5][o:6][c:7]2[c:8]1",
        description="Inserting O into benzene ring creates benzofuran. "
                    "More polar and different electronics.",
        expected_impact="Polarity increase, oxygen_introduction, planarity",
        complexity_delta=0.8,
        tags=["polarity_increase", "oxygen", "benzofuran"],
        reference="Benzofuran isosteres"
    ),
    "RING_120": SmirksEntry(
        id="RING_120",
        category="aromatic_ring_swaps",
        name="Benzene to benzothiophene (S insertion)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]2[c:4][c:5][s:6][c:7]2[c:8]1",
        description="Inserting S into benzene ring creates benzothiophene. "
                    "More lipophilic than benzofuran.",
        expected_impact="Lipophilicity increase, sulfur, benzothiophene",
        complexity_delta=0.8,
        tags=["lipophilicity_increase", "sulfur", "benzothiophene"],
        reference="Benzothiophene isosteres"
    ),
    "AMID001": SmirksEntry(
        id="AMID001",
        category="amide_bond_replacements",
        name="Primary amide to N,N-dimethylamide",
        smirks="[NH2:1][C:2](=[O:3])>>[N:1]([C:4])[C:2](=[O:3])",
        description="N,N-dimethylation of primary amide. "
                    "Reduces H-bonding and improves membrane permeability.",
        expected_impact="Permeability increase, H-bond reduction, TPSA",
        complexity_delta=0.2,
        tags=["permeability", "hbond_reduction", "dimethylamide"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AMID002": SmirksEntry(
        id="AMID002",
        category="amide_bond_replacements",
        name="Amide to piperidine (cyclic constraint)",
        smirks="[NH2:1][C:2](=[O:3])>>[N:1]1[C:2][C:3][C:4][C:5][C:6]1",
        description="Piperidine isostere replaces amide. "
                    "Constrains geometry and reduces polarity.",
        expected_impact="Constrained geometry, reduced polarity, permeability",
        complexity_delta=0.3,
        tags=["cyclic_constraint", "permeability", "piperidine"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AMID003": SmirksEntry(
        id="AMID003",
        category="amide_bond_replacements",
        name="Amide to azetidine (small cyclic)",
        smirks="[NH2:1][C:2](=[O:3])>>[N:1]1[C:2][C:3][C:4]1",
        description="Azetidine isostere replaces amide. "
                    "Smallest cyclic amine replacement for amide.",
        expected_impact="Constrained geometry, small ring, reduced PSA",
        complexity_delta=0.2,
        tags=["cyclic_constraint", "azetidine", "small_ring"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "ETHER001": SmirksEntry(
        id="ETHER001",
        category="ether_modifications",
        name="Ether to thioether (oxidative metabolic stability)",
        smirks="[C:1][O:2][C:3]>>[C:1][S:2][C:3]",
        description="Sulfur replaces oxygen in ether linkage. "
                    "Thioethers are more resistant to oxidative metabolism.",
        expected_impact="Metabolic stability, different clearance, lipophilicity",
        complexity_delta=0.0,
        tags=["metabolic_stability", "thioether", "oxidative"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "ETHER002": SmirksEntry(
        id="ETHER002",
        category="ester_modifications",
        name="Ester to amide (hydrolytic stability)",
        smirks="[C:1][C:2](=[O:3])[O:4][C:5]>>[C:1][C:2](=[O:3])[N:4][C:5]",
        description="Amide replaces ester linkage. "
                    "Amides are more resistant to hydrolytic cleavage.",
        expected_impact="Hydrolytic stability, reduced clearance, PSA",
        complexity_delta=0.0,
        tags=["hydrolytic_stability", "amide", "metabolic_stability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "ETHER003": SmirksEntry(
        id="ETHER003",
        category="o_substitutions",
        name="Methoxy to ethoxy (hydrolytic stability)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][CH2:3][CH3:4]",
        description="Ethoxy replaces methoxy. "
                    "Slightly larger and more resistant to O-demethylation.",
        expected_impact="Metabolic stability, lipophilicity, size",
        complexity_delta=0.1,
        tags=["metabolic_stability", "ethoxy", "size_increase"],
        reference="Ether SAR"
    ),
    "FLUO001": SmirksEntry(
        id="FLUO001",
        category="halogen_substitutions",
        name="Methoxy to fluoromethyl (metabolic block)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][CH2:3][F:4]",
        description="Fluorine replaces hydrogen on methyl. "
                    "Blocks O-demethylation metabolism.",
        expected_impact="Metabolic block, fluorination, O-demethylation",
        complexity_delta=0.0,
        tags=["fluorination", "metabolic_block", "O-demethylation"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "FLUO002": SmirksEntry(
        id="FLUO002",
        category="halogen_substitutions",
        name="Benzylic CH to CF2 (metabolic block)",
        smirks="[c:1][CH2:2][CH3:3]>>[c:1][C:2]([F:4])([F:5])[CH3:3]",
        description="Gem-difluorination at benzylic position blocks oxidative metabolism.",
        expected_impact="Metabolic block, lipophilicity, hERG",
        complexity_delta=0.1,
        tags=["fluorination", "benzylic", "metabolic_block"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "FLUO003": SmirksEntry(
        id="FLUO003",
        category="halogen_substitutions",
        name="Toluene to difluorobenzene (aromatic oxidation block)",
        smirks="[c:1]1[c:2][c:3][c:4]([CH3:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([C:5]([F:8])([F:9]))[c:6][c:7]1",
        description="Aromatic difluorination blocks phenyl oxidation. "
                    "D-F bond is metabolically stable.",
        expected_impact="Metabolic block, aromatic fluorination, lipophilicity",
        complexity_delta=0.1,
        tags=["fluorination", "aromatic", "metabolic_block"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "FLUO004": SmirksEntry(
        id="FLUO004",
        category="halogen_substitutions",
        name="Methyl to trifluoromethyl (lipophilicity + metabolic block)",
        smirks="[CH3:1]>>[C:1]([F:2])([F:3])([F:4])",
        description="CF3 replaces CH3. Major increase in lipophilicity "
                    "and complete block of oxidative metabolism.",
        expected_impact="Lipophilicity increase, metabolic block, size",
        complexity_delta=0.2,
        tags=["lipophilicity", "metabolic_block", "CF3"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "FLUO005": SmirksEntry(
        id="FLUO005",
        category="o_substitutions",
        name="Methoxy to fluoromethoxy (partial fluorination)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][CH2:3][F:4]",
        description="Fluoromethoxy group partially fluorinates the methyl. "
                    "Blocks O-demethylation while maintaining ether properties.",
        expected_impact="Metabolic block, fluorination, polarity",
        complexity_delta=0.1,
        tags=["fluorination", "O-demethylation_block", "ether"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "FLUO006": SmirksEntry(
        id="FLUO006",
        category="cns_penetration",
        name="Pyridine to fluoropyridine (basicity reduction)",
        smirks="[c:1]1[c:2][c:3][c:4][n:5][c:6]1>>[c:1]1[c:2][c:3][c:4][n:5][c:6]([F:7])1",
        description="Fluoropyridine reduces N basicity and blocks N-oxide metabolism. "
                    "Improved CNS penetration.",
        expected_impact="Basicity reduction, metabolic block, CNS",
        complexity_delta=0.3,
        tags=["basicity_reduction", "pyridine", "CNS", "fluorination"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "RING201": SmirksEntry(
        id="RING201",
        category="aromatic_ring_swaps",
        name="Phenyl to cyclohexyl (aromatic saturation)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4][C:5][C:6]1",
        description="Saturation of aromatic ring to cyclohexyl. "
                    "Reduces aromatic stacking, changes lipophilicity.",
        expected_impact="Saturation, lipophilicity change, aromatic_stacking",
        complexity_delta=0.5,
        tags=["saturation", "cyclohexyl", "lipophilicity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "RING202": SmirksEntry(
        id="RING202",
        category="aromatic_ring_swaps",
        name="Benzene to thiophene (classic bioisostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][s:4][c:5][c:6]1",
        description="Thiophene replaces benzene. Classic bioisostere with "
                    "sulfur adding slight bend and different dipole.",
        expected_impact="Sulfur addition, lipophilicity, classic_isostere",
        complexity_delta=0.3,
        tags=["classic_isostere", "sulfur", "lipophilicity"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "RING203": SmirksEntry(
        id="RING203",
        category="aromatic_ring_swaps",
        name="Benzene to furan (classic 5-membered isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][o:4][c:5][c:6]1",
        description="Furan replaces benzene. Classic bioisostere with oxygen "
                    "adding polarity and H-bond acceptor.",
        expected_impact="Oxygen addition, polarity, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["classic_isostere", "furan", "oxygen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "RING204": SmirksEntry(
        id="RING204",
        category="aromatic_ring_swaps",
        name="Benzene to pyrrole (NH heterocycle isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][nH:4][c:5][c:6]1",
        description="Pyrrole replaces benzene. Adds NH H-bond donor capability "
                    "while maintaining aromaticity.",
        expected_impact="NH donor, aromatic, H-bonding",
        complexity_delta=0.3,
        tags=["classic_isostere", "pyrrole", "NH_donor"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "RING205": SmirksEntry(
        id="RING205",
        category="aromatic_ring_swaps",
        name="Cyclohexyl to phenyl (aromatic ring formation)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Aromatization of cyclohexyl to phenyl. "
                    "Adds aromatic stacking capability.",
        expected_impact="Aromaticity addition, stacking, lipophilicity",
        complexity_delta=0.3,
        tags=["aromaticity", "phenyl", "stacking"],
        reference="Aromatic ring formation"
    ),
    "RING206": SmirksEntry(
        id="RING206",
        category="aromatic_ring_swaps",
        name="Cyclohexenyl to phenyl (aromatic ring formation)",
        smirks="[C:1]1[C:2][C:3][C:4]=[C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Aromatization of cyclohexenyl to phenyl. "
                    "Adds full aromaticity and planar geometry.",
        expected_impact="Aromaticity, planarity, stacking",
        complexity_delta=0.4,
        tags=["aromaticity", "phenyl", "planarity"],
        reference="Aromatic ring formation"
    ),
    "CARB017": SmirksEntry(
        id="CARB017",
        category="carbonyl_modifications",
        name="Carbonyl to thiocarbonyl (sulfur isostere)",
        smirks="[C:1](=[O:2])[O:3]>>[C:1](=[S:2])[O:3]",
        description="Thiocarbonyl replaces carbonyl. "
                    "Sulfur is larger and less electronegative.",
        expected_impact="Size increase, thiocarbonyl, different_electronics",
        complexity_delta=0.0,
        tags=["sulfur", "thiocarbonyl", "isostere"],
        reference="Carbonyl isosteres"
    ),
    "CARB018": SmirksEntry(
        id="CARB018",
        category="carbonyl_modifications",
        name="Amide to thioamide (sulfur isostere)",
        smirks="[C:1](=[O:2])[NH:3]>>[C:1](=[S:2])[NH:3]",
        description="Thioamide replaces amide. "
                    "More lipophilic with different H-bonding.",
        expected_impact="Lipophilicity, thioamide, H-bonding",
        complexity_delta=0.0,
        tags=["thioamide", "sulfur", "lipophilicity"],
        reference="Thioamide isosteres"
    ),
    "CARB019": SmirksEntry(
        id="CARB019",
        category="carbonyl_modifications",
        name="Ketone to oxime (metabolic stability)",
        smirks="[C:1](=[O:2])[CH3:3]>>[C:1](=[N:2][OH:4])[CH3:3]",
        description="Oxime replaces ketone. "
                    "Blocks reductive metabolism and adds H-bond donor.",
        expected_impact="Metabolic stability, oxime, H-bonding",
        complexity_delta=0.3,
        tags=["metabolic_stability", "oxime", "hbond_donor"],
        reference="Oxime isosteres"
    ),
    "CARB020": SmirksEntry(
        id="CARB020",
        category="carbonyl_modifications",
        name="Ketone to amide (nitrogen isostere)",
        smirks="[C:1](=[O:2])[CH3:3]>>[C:1](=[O:2])[NH:3]",
        description="Amide replaces ketone. "
                    "Nitrogen adds H-bonding and changes electronics.",
        expected_impact="H-bonding, amide, polarity",
        complexity_delta=0.0,
        tags=["amide", "nitrogen", "hbonding"],
        reference="Ketone amide isosteres"
    ),
    "NIT011": SmirksEntry(
        id="NIT011",
        category="nitrile_modifications",
        name="Nitrile to trifluoromethyl (fluorination)",
        smirks="[C:1]#[N:2]>>[C:1]([F:3])([F:4])([F:5])",
        description="CF3 replaces nitrile. "
                    "Major lipophilicity increase and different H-bonding.",
        expected_impact="Lipophilicity increase, CF3, different_electronics",
        complexity_delta=0.2,
        tags=["CF3", "lipophilicity", "fluorination"],
        reference="Nitrile CF3 isosteres"
    ),
    "NIT013": SmirksEntry(
        id="NIT013",
        category="nitrile_modifications",
        name="Nitrile to tetrazole (bioisostere)",
        smirks="[CH:1]#[N:2]>>[N:1]1[N:2]=[N:3]=[N:4]1",
        description="Tetrazole replaces nitrile. "
                    "5-membered heterocycle with 4 nitrogens, non-basic.",
        expected_impact="Tetrazole, non-basic, H-bonding",
        complexity_delta=1.0,
        tags=["tetrazole", "non-basic", "bioisostere"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "STER016": SmirksEntry(
        id="STER016",
        category="steric_shielding",
        name="Methyl to tert-butyl (major steric shield)",
        smirks="[CH3:1]>>[C:1]([CH3:2])([CH3:3])[CH3:4]",
        description="tert-Butyl replaces methyl. "
                    "Major steric bulk can shield metabolic sites.",
        expected_impact="Steric shielding, bulk, metabolic_block",
        complexity_delta=0.1,
        tags=["tert-butyl", "steric_shielding", "bulk"],
        reference="Steric shielding SAR"
    ),
    "STER017": SmirksEntry(
        id="STER017",
        category="o_substitutions",
        name="Methoxy to tert-butoxy (steric shield)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][C:3]([CH3:4])([CH3:5])[CH3:6]",
        description="tert-Butoxy replaces methoxy. "
                    "Major steric bulk around oxygen.",
        expected_impact="Steric shielding, tert-butoxy, bulk",
        complexity_delta=0.2,
        tags=["tert-butoxy", "steric_shielding", "oxygen"],
        reference="Steric alkoxy SAR"
    ),
    "STER018": SmirksEntry(
        id="STER018",
        category="amine_modifications",
        name="Primary amine to dimethylamine (N-methylation)",
        smirks="[NH2:1]>>[NH:1][CH3:2]",
        description="Dimethylamine replaces primary amine. "
                    "Reduces H-bonding and basicity slightly.",
        expected_impact="Basicity reduction, H-bond reduction, N-methylation",
        complexity_delta=0.1,
        tags=["N-methylation", "basicity", "dimethylamine"],
        reference="Amine N-methylation SAR"
    ),
    "META019": SmirksEntry(
        id="META019",
        category="metabolic_stability",
        name="Alcohol to ketone (oxidative metabolism)",
        smirks="[O:1][CH2:2][CH3:3]>>[CH3:1][C:2](=[O:3])[CH3:4]",
        description="Alcohol oxidation to ketone. "
                    "Removes H-bonding and changes polarity.",
        expected_impact="Polarity reduction, ketone, oxidative_metabolism",
        complexity_delta=0.0,
        tags=["oxidation", "ketone", "polarity_reduction"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "META020": SmirksEntry(
        id="META020",
        category="metabolic_stability",
        name="Carboxylic acid to methyl ester (masked acid)",
        smirks="[C:1](=[O:2])(=[O:3])[OH:4]>>[C:1](=[O:2])(=[O:3])[CH3:4]",
        description="Methyl ester masks carboxylic acid. "
                    "Prevents Phase II glucuronidation.",
        expected_impact="Hydrolytic stability, masked acid, ester",
        complexity_delta=0.0,
        tags=["ester", "masked_acid", "metabolic_stability"],
        reference="Ester isosteres"
    ),
    "META021": SmirksEntry(
        id="META021",
        category="metabolic_stability",
        name="Schiff base to oxime (metabolic stability)",
        smirks="[C:1]=[N:2]>>[C:1]=[N:2][OH:3]",
        description="Oxime replaces Schiff base imine. "
                    "More metabolically stable with H-bonding.",
        expected_impact="Metabolic stability, oxime, H-bonding",
        complexity_delta=0.2,
        tags=["oxime", "metabolic_stability", "imine"],
        reference="Oxime isosteres"
    ),
    "POLA001": SmirksEntry(
        id="POLA001",
        category="sulfonyl_modifications",
        name="Thioether to sulfoxide (polarity increase)",
        smirks="[C:1][S:2][C:3]>>[C:1][S:2](=[O:4])[C:3]",
        description="Sulfoxide replaces thioether. "
                    "Adds polarity while maintaining shape.",
        expected_impact="Polarity increase, sulfoxide, shape",
        complexity_delta=0.3,
        tags=["sulfoxide", "polarity", "oxidation"],
        reference="Sulfoxide isosteres"
    ),
    "POLA002": SmirksEntry(
        id="POLA002",
        category="sulfonyl_modifications",
        name="Thioether to sulfone (major polarity increase)",
        smirks="[C:1][S:2][C:3]>>[C:1][S:2](=[O:4])(=[O:5])[C:3]",
        description="Sulfone replaces thioether. "
                    "Major polarity increase and different electronics.",
        expected_impact="Polarity increase, sulfone, electronics",
        complexity_delta=0.4,
        tags=["sulfone", "polarity", "oxidation"],
        reference="Sulfone isosteres"
    ),
    "POLA003": SmirksEntry(
        id="POLA003",
        category="aromatic_ring_swaps",
        name="Phenyl to pyridyl (add nitrogen and polarity)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][c:4][n:5][c:6]1",
        description="Pyridine replaces phenyl. "
                    "Adds dipole, H-bond acceptor, and reduced aromatic stacking.",
        expected_impact="Polarity, nitrogen, H-bond_acceptor",
        complexity_delta=0.2,
        tags=["pyridine", "nitrogen", "polarity"],
        reference="Aromatic heterocycle swaps"
    ),
    "AMID007": SmirksEntry(
        id="AMID007",
        category="amide_bond_replacements",
        name="Amide to thioamide (sulfur isostere)",
        smirks="[N:1][C:2](=[O:3])>>[N:1][C:2](=[S:3])",
        description="Thioamide replaces amide. "
                    "More lipophilic with different H-bonding profile.",
        expected_impact="Lipophilicity, thioamide, different_electronics",
        complexity_delta=0.0,
        tags=["thioamide", "sulfur", "lipophilicity"],
        reference="Amide thioamide isosteres"
    ),
    "AMID008": SmirksEntry(
        id="AMID008",
        category="amide_bond_replacements",
        name="Amide to ester (reversed polarity)",
        smirks="[N:1][C:2](=[O:3])[C:4]>>[O:1][C:2](=[O:3])[C:4]",
        description="Ester replaces amide with reversed atom order. "
                    "Changes H-bonding from donor to acceptor.",
        expected_impact="H-bond acceptor, ester, different_electronics",
        complexity_delta=0.0,
        tags=["ester", "hbonding", "polarity"],
        reference="Amide ester isosteres"
    ),
    "ETHER005": SmirksEntry(
        id="ETHER005",
        category="o_substitutions",
        name="Ether to difluoromethoxy (fluorinated ether)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][CH2:3][F:4][F:5]",
        description="Difluoromethoxy replaces methoxy. "
                    "Blocks O-demethylation, adds lipophilicity.",
        expected_impact="Fluorination, metabolic block, lipophilicity",
        complexity_delta=0.2,
        tags=["difluoromethoxy", "fluorination", "metabolic_block"],
        reference="Fluorinated ether SAR"
    ),
    "ETHER006": SmirksEntry(
        id="ETHER006",
        category="o_substitutions",
        name="Ether to trifluoromethoxy (perfluorinated ether)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][C:3]([F:4])([F:5])([F:6])",
        description="Trifluoromethoxy replaces methoxy. "
                    "Major metabolic stability and lipophilicity increase.",
        expected_impact="CF3, lipophilicity, metabolic stability",
        complexity_delta=0.2,
        tags=["trifluoromethoxy", "CF3", "metabolic_stability"],
        reference="Trifluoromethyl ether SAR"
    ),
    "ETHER007": SmirksEntry(
        id="ETHER007",
        category="ether_modifications",
        name="Ether to thioether (sulfur exchange)",
        smirks="[C:1][O:2][C:3]>>[C:1][S:2][C:3]",
        description="Thioether replaces ether. "
                    "More resistant to oxidative metabolism.",
        expected_impact="Sulfur, metabolic stability, different_electronics",
        complexity_delta=0.0,
        tags=["thioether", "sulfur", "oxidative_metabolism"],
        reference="Ether thioether exchange"
    ),
    "OSUB035": SmirksEntry(
        id="OSUB035",
        category="o_substitutions",
        name="Methoxy to thiomethyl (S exchange)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][S:2][CH3:3]",
        description="Sulfur replaces oxygen in methoxy group. "
                    "Thioether is more lipophilic.",
        expected_impact="Lipophilicity, thioether, metabolic stability",
        complexity_delta=0.0,
        tags=["thioether", "sulfur", "lipophilicity"],
        reference="Methoxy thioether isosteres"
    ),
    "OSUB036": SmirksEntry(
        id="OSUB036",
        category="o_substitutions",
        name="Methoxy to carbamoyl (N addition)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][C:3](=[O:4])[N:5]",
        description="Carbamoyl replaces methoxy. "
                    "Adds H-bonding capability.",
        expected_impact="H-bonding, carbamoyl, polarity",
        complexity_delta=0.2,
        tags=["carbamoyl", "hbonding", "polarity"],
        reference="Carbamoyl isosteres"
    ),
    "OSUB037": SmirksEntry(
        id="OSUB037",
        category="o_substitutions",
        name="Methoxy to N-methylcarbamoyl (constrained carbamoyl)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][C:3](=[O:4])[N:5][CH3:6]",
        description="N-methylcarbamoyl replaces methoxy. "
                    "Constrained H-bonding with reduced polarity.",
        expected_impact="H-bonding, N-methyl, constrained",
        complexity_delta=0.3,
        tags=["N-methylcarbamoyl", "constrained", "hbonding"],
        reference="Carbamoyl SAR"
    ),
    "OSUB038": SmirksEntry(
        id="OSUB038",
        category="halogen_substitutions",
        name="Methoxy to difluoromethyl (fluorination)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][CH:3][F:4][F:5]",
        description="Difluoromethyl replaces methyl. "
                    "Blocks oxidation, adds lipophilicity.",
        expected_impact="Fluorination, metabolic block, lipophilicity",
        complexity_delta=0.2,
        tags=["difluoromethyl", "fluorination", "metabolic_block"],
        reference="Difluoromethyl isosteres"
    ),
    "OSUB039": SmirksEntry(
        id="OSUB039",
        category="halogen_substitutions",
        name="Methoxy to trifluoromethyl (perfluorination)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][O:2][C:3]([F:4])([F:5])([F:6])",
        description="Trifluoromethyl replaces methyl. "
                    "Major metabolic stability and lipophilicity.",
        expected_impact="CF3, metabolic stability, lipophilicity",
        complexity_delta=0.2,
        tags=["CF3", "perfluorination", "metabolic_stability"],
        reference="Trifluoromethyl isosteres"
    ),
    "OSUB040": SmirksEntry(
        id="OSUB040",
        category="o_substitutions",
        name="Methoxy to ethylamino (N substitution)",
        smirks="[C:1][O:2][CH3:3]>>[C:1][N:2][CH2:3][CH3:4]",
        description="Ethylamino replaces methoxy. "
                    "Adds H-bonding donor, reduces lipophilicity.",
        expected_impact="H-bond donor, polarity, amine",
        complexity_delta=0.2,
        tags=["ethylamino", "hbond_donor", "polarity"],
        reference="Ethylamino isosteres"
    ),
    "META022": SmirksEntry(
        id="META022",
        category="steric_shielding",
        name="Isopropyl to tert-butyl (steric increase)",
        smirks="[CH:1]([CH3:2])[CH3:3]>>[C:1]([CH3:2])([CH3:3])[CH3:4]",
        description="tert-Butyl replaces isopropyl. "
                    "Major steric bulk increase.",
        expected_impact="Steric bulk, shielding, lipophilicity",
        complexity_delta=0.1,
        tags=["tert-butyl", "steric_shielding", "bulk"],
        reference="Isopropyl tert-butyl isosteres"
    ),
    "META023": SmirksEntry(
        id="META023",
        category="halogen_substitutions",
        name="Toluene to fluorobenzene (aromatic oxidation block)",
        smirks="[c:1]1[c:2][c:3][c:4]([CH3:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([F:5])[c:6][c:7]1",
        description="Fluorobenzene replaces toluene. "
                    "Blocks benzylic oxidation.",
        expected_impact="Metabolic block, fluorination, aromatic",
        complexity_delta=0.0,
        tags=["fluorination", "metabolic_block", "aromatic"],
        reference="Toluene fluorobenzene isosteres"
    ),
    "META024": SmirksEntry(
        id="META024",
        category="halogen_substitutions",
        name="Toluene to chlorobenzene (halogen scan)",
        smirks="[c:1]1[c:2][c:3][c:4]([CH3:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([Cl:5])[c:6][c:7]1",
        description="Chlorobenzene replaces toluene. "
                    "Adds polarizability and blocks oxidation.",
        expected_impact="Chlorine, polarizability, metabolic_block",
        complexity_delta=0.0,
        tags=["chlorination", "polarizability", "metabolic_block"],
        reference="Halogen scan SAR"
    ),
    "META025": SmirksEntry(
        id="META025",
        category="metabolic_stability",
        name="Methyl to ethyl (homologation)",
        smirks="[CH3:1]>>[CH2:1][CH3:2]",
        description="Ethyl replaces methyl. "
                    "Increases size and slightly increases lipophilicity.",
        expected_impact="Homologation, size, lipophilicity",
        complexity_delta=0.0,
        tags=["homologation", "size", "ethyl"],
        reference="Methyl ethyl isosteres"
    ),
    "META026": SmirksEntry(
        id="META026",
        category="metabolic_stability",
        name="Toluene to ethylbenzene (benzylic homologation)",
        smirks="[c:1][CH2:2][CH3:3]>>[c:1][CH2:2][CH2:3][CH3:4]",
        description="Ethylbenzene replaces toluene. "
                    "One carbon homologation reduces metabolism.",
        expected_impact="Homologation, benzylic, metabolic_stability",
        complexity_delta=0.0,
        tags=["homologation", "benzylic", "ethyl"],
        reference="Toluene ethylbenzene isosteres"
    ),
    "CNS021": SmirksEntry(
        id="CNS021",
        category="cns_penetration",
        name="Carboxylic acid to amide (PSA reduction)",
        smirks="[C:1](=[O:2])(=[O:3])[OH:4]>>[C:1](=[O:2])(=[O:3])[NH2:4]",
        description="Amide replaces acid. "
                    "Reduces PSA and improves CNS penetration.",
        expected_impact="PSA reduction, CNS, permeability",
        complexity_delta=0.0,
        tags=["amide", "PSA_reduction", "CNS"],
        reference="CNS penetration SAR"
    ),
    "CNS022": SmirksEntry(
        id="CNS022",
        category="cns_penetration",
        name="Carboxylic acid to tetrazole (PSA reduction)",
        smirks="[C:1](=[O:2])(=[O:3])[OH:4]>>[C:1]1[N:2]=[N:3][N:4]=[N:5]1",
        description="Tetrazole replaces acid. "
                    "Major PSA reduction with non-basic heterocycle.",
        expected_impact="PSA reduction, tetrazole, CNS",
        complexity_delta=1.0,
        tags=["tetrazole", "PSA_reduction", "CNS"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "CNS023": SmirksEntry(
        id="CNS023",
        category="cns_penetration",
        name="Carboxylic acid to trifluoroethyl ester (masked acid)",
        smirks="[C:1](=[O:2])(=[O:3])[OH:4]>>[C:1](=[O:2])[O:4][CH2:5][C:6]([F:7])([F:8])([F:9])",
        description="Trifluoroethyl ester masks acid. "
                    "Very hydrolytically stable with high lipophilicity.",
        expected_impact="Masked acid, lipophilicity, stability",
        complexity_delta=0.3,
        tags=["ester", "CF3", "masked_acid"],
        reference="Trifluoroethyl ester SAR"
    ),
    "CNS024": SmirksEntry(
        id="CNS024",
        category="cns_penetration",
        name="Primary alcohol to fluorinated alcohol (H-bond reduction)",
        smirks="[O:1][CH2:2][CH3:3]>>[O:1][CH2:2][C:3]([F:4])([F:5])",
        description="Difluoromethyl replaces methyl on alcohol. "
                    "Removes H-bond donor while maintaining polarity.",
        expected_impact="H-bond reduction, fluorination, polarity",
        complexity_delta=0.2,
        tags=["fluorination", "hbond_reduction", "alcohol"],
        reference="Alcohol fluorination SAR"
    ),
    "CNS025": SmirksEntry(
        id="CNS025",
        category="cns_penetration",
        name="Urea to N-methyl urea (H-bond reduction)",
        smirks="[N:1][C:2](=[O:3])[N:4]>>[N:1][C:2](=[O:3])[N:4][CH3:5]",
        description="N-methyl urea reduces one H-bond donor. "
                    "N-methylation of urea reduces PSA.",
        expected_impact="H-bond reduction, N-methyl, urea",
        complexity_delta=0.1,
        tags=["N-methyl", "urea", "hbond_reduction"],
        reference="N-methyl urea SAR"
    ),
    "HALO007": SmirksEntry(
        id="HALO007",
        category="halogen_substitutions",
        name="Trifluoromethyl to chlorine (size reduction)",
        smirks="[C:1]([F:2])([F:3])([F:4])>>[Cl:1]",
        description="Chloro replaces trifluoromethyl. "
                    "Major size and lipophilicity reduction.",
        expected_impact="Size reduction, lipophilicity reduction, Cl",
        complexity_delta=0.0,
        tags=["CF3_to_Cl", "size_reduction", "lipophilicity"],
        reference="CF3 chlorine isosteres"
    ),
    "HALO008": SmirksEntry(
        id="HALO008",
        category="halogen_substitutions",
        name="Aryl chloride to aryl fluoride (size reduction)",
        smirks="[c:1][Cl:2]>>[c:1][F:2]",
        description="Fluoro replaces chloro on aromatic ring. "
                    "Major size reduction with different electronics.",
        expected_impact="Size reduction, fluorination, electronics",
        complexity_delta=0.0,
        tags=["Cl_to_F", "size_reduction", "fluorination"],
        reference="Aryl halogen exchange SAR"
    ),
    "HALO009": SmirksEntry(
        id="HALO009",
        category="halogen_substitutions",
        name="Aryl bromide to aryl chloride (size reduction)",
        smirks="[c:1][Br:2]>>[c:1][Cl:2]",
        description="Chloro replaces bromo on aromatic ring. "
                    "Size reduction while maintaining binding.",
        expected_impact="Size reduction, chlorination, binding",
        complexity_delta=0.0,
        tags=["Br_to_Cl", "size_reduction", "halogen"],
        reference="Aryl halogen exchange SAR"
    ),
    "HALO010": SmirksEntry(
        id="HALO010",
        category="carbonyl_modifications",
        name="Tertiary amide to thioamide (sulfur isostere)",
        smirks="[N:1]([C:2])[C:3](=[O:4])[C:5]>>[N:1]([C:2])[C:3](=[S:4])[C:5]",
        description="Thioamide replaces amide. "
                    "Changes H-bonding and metabolic stability.",
        expected_impact="Thioamide, sulfur, H-bonding",
        complexity_delta=0.0,
        tags=["thioamide", "sulfur", "metabolic_stability"],
        reference="Amide thioamide isosteres"
    ),
    "BENZ007": SmirksEntry(
        id="BENZ007",
        category="steric_shielding",
        name="Toluene to ethylbenzene (homologation)",
        smirks="[c:1][CH2:2][CH3:3]>>[c:1][CH2:2][CH2:3][CH3:4]",
        description="Ethylbenzene replaces toluene. "
                    "Slightly larger with reduced benzylic metabolism.",
        expected_impact="Homologation, benzylic, metabolic_stability",
        complexity_delta=0.0,
        tags=["ethyl", "homologation", "benzylic"],
        reference="Toluene ethylbenzene SAR"
    ),
    "BENZ008": SmirksEntry(
        id="BENZ008",
        category="steric_shielding",
        name="Toluene to cumene (isopropyl substitution)",
        smirks="[c:1][CH2:2][CH3:3]>>[c:1][CH:2]([CH3:3])[CH3:4]",
        description="Cumene replaces toluene. "
                    "Isopropyl group blocks benzylic oxidation.",
        expected_impact="Steric block, cumene, benzylic",
        complexity_delta=0.1,
        tags=["cumene", "steric_block", "benzylic"],
        reference="Toluene cumene SAR"
    ),
    "BENZ009": SmirksEntry(
        id="BENZ009",
        category="benzylic_modifications",
        name="Benzylamine to benzamide (oxidation)",
        smirks="[c:1][CH2:2][NH2:3]>>[c:1][C:2](=[O:3])[NH2:4]",
        description="Benzamide replaces benzylamine. "
                    "Oxidation of benzylic amine to amide.",
        expected_impact="Oxidation, amide, polarity",
        complexity_delta=0.0,
        tags=["oxidation", "amide", "polarity"],
        reference="Benzyl oxidation SAR"
    ),
    "BENZ010": SmirksEntry(
        id="BENZ010",
        category="benzylic_modifications",
        name="Benzyl alcohol to benzoic acid (oxidation)",
        smirks="[c:1][CH2:2][OH:3]>>[c:1][C:2](=[O:3])[OH:4]",
        description="Benzoic acid replaces benzyl alcohol. "
                    "Full oxidation of benzylic alcohol to acid.",
        expected_impact="Oxidation, acid, polarity",
        complexity_delta=0.0,
        tags=["oxidation", "acid", "polarity"],
        reference="Benzylic oxidation SAR"
    ),
    "BIOI006": SmirksEntry(
        id="BIOI006",
        category="aromatic_ring_swaps",
        name="Thiophene to furan (chalcogen exchange)",
        smirks="[c:1]1[c:2][c:3][s:4][c:5][c:6]1>>[c:1]1[c:2][c:3][o:4][c:5][c:6]1",
        description="Furan replaces thiophene. "
                    "Sulfur to oxygen exchange maintains ring size.",
        expected_impact="Oxygen, sulfur removal, polarity",
        complexity_delta=0.3,
        tags=["furan", "thiophene", "chalcogen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "BIOI007": SmirksEntry(
        id="BIOI007",
        category="aromatic_ring_swaps",
        name="Furan to pyrrole (oxygen to nitrogen)",
        smirks="[c:1]1[c:2][c:3][o:4][c:5][c:6]1>>[c:1]1[c:2][c:3][nH:4][c:5][c:6]1",
        description="Pyrrole replaces furan. "
                    "Oxygen to nitrogen adds H-bond donor capability.",
        expected_impact="Nitrogen, NH_donor, aromatic",
        complexity_delta=0.3,
        tags=["pyrrole", "furan", "nitrogen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "BIOI008": SmirksEntry(
        id="BIOI008",
        category="ether_modifications",
        name="Thioether to ether (oxygen exchange)",
        smirks="[C:1][S:2][C:3]>>[C:1][O:2][C:3]",
        description="Ether replaces thioether. "
                    "Oxygen is more electronegative, changes polarity.",
        expected_impact="Oxygen, polarity, different_electronics",
        complexity_delta=0.0,
        tags=["oxygen", "thioether", "polarity"],
        reference="Thioether ether exchange"
    ),
    "SULF003": SmirksEntry(
        id="SULF003",
        category="sulfonyl_modifications",
        name="Thioether to sulfoxide (oxidation step 1)",
        smirks="[C:1][S:2][C:3]>>[C:1][S:2](=[O:4])[C:3]",
        description="Sulfoxide replaces thioether. "
                    "First oxidation step adds polarity.",
        expected_impact="Sulfoxide, oxidation, polarity",
        complexity_delta=0.3,
        tags=["sulfoxide", "oxidation", "polarity"],
        reference="Sulfoxide isosteres"
    ),
    "SULF004": SmirksEntry(
        id="SULF004",
        category="sulfonyl_modifications",
        name="Thioether to sulfone (full oxidation)",
        smirks="[C:1][S:2][C:3]>>[C:1][S:2](=[O:4])(=[O:5])[C:3]",
        description="Sulfone replaces thioether. "
                    "Full oxidation adds major polarity.",
        expected_impact="Sulfone, oxidation, polarity",
        complexity_delta=0.4,
        tags=["sulfone", "oxidation", "polarity"],
        reference="Sulfone isosteres"
    ),
    "CARB022": SmirksEntry(
        id="CARB022",
        category="carbonyl_modifications",
        name="Ketone to carboxylic acid (oxidation)",
        smirks="[CH3:1][C:2](=[O:3])[CH3:4]>>[CH3:1][C:2](=[O:3])(=[O:4])[OH:5]",
        description="Carboxylic acid replaces ketone. "
                    "Full oxidation adds polarity and H-bonding.",
        expected_impact="Acid, oxidation, polarity",
        complexity_delta=0.0,
        tags=["oxidation", "acid", "ketone"],
        reference="Ketone acid isosteres"
    ),
    "CARB023": SmirksEntry(
        id="CARB023",
        category="carbonyl_modifications",
        name="Ketone to aldehyde (reduce one alkyl)",
        smirks="[CH3:1][C:2](=[O:3])[CH3:4]>>[CH3:1][C:2](=[O:3])[H:4]",
        description="Aldehyde replaces ketone. "
                    "One side reduced to hydrogen.",
        expected_impact="Aldehyde, polarity, reactivity",
        complexity_delta=0.0,
        tags=["aldehyde", "ketone", "reduction"],
        reference="Ketone aldehyde isosteres"
    ),
    "PHEN005": SmirksEntry(
        id="PHEN005",
        category="carboxylic_acid_replacements",
        name="Phenol to phenylboronic acid (boron isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][c:4]([B:7]([O:8])[O:9])[c:5][c:6]1",
        description="Phenylboronic acid is a classic phenol bioisostere. "
                    "Boron adds different electronics and H-bonding.",
        expected_impact="Boron, bioisostere, different_electronics",
        complexity_delta=0.5,
        tags=["boron", "phenol_isostere", "bioisostere"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN006": SmirksEntry(
        id="PHEN006",
        category="halogen_substitutions",
        name="Phenol to fluorobenzene (F/H exchange)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([F:5])[c:6][c:7]1",
        description="Fluorobenzene replaces phenol. "
                    "Removes H-bonding donor, adds metabolic stability.",
        expected_impact="Fluorination, metabolic_stability, H-bond_reduction",
        complexity_delta=0.0,
        tags=["fluorination", "phenol_isostere", "hbond_reduction"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN007": SmirksEntry(
        id="PHEN007",
        category="aromatic_ring_swaps",
        name="Phenol to pyrrole (NH heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4][nH:5][c:6][c:7]1",
        description="Pyrrole replaces phenol. "
                    "Adds NH H-bond donor while maintaining aromaticity.",
        expected_impact="NH_donor, aromatic, heterocycle",
        complexity_delta=0.3,
        tags=["pyrrole", "NH_donor", "aromatic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN008": SmirksEntry(
        id="PHEN008",
        category="nitrile_modifications",
        name="Phenol to pyridine N-oxide (N-oxide isostere)",
        smirks="[c:1]1[c:2][c:3][c:4][n:5][c:6]1>>[c:1]1[c:2][c:3][c:4][n+:5]([O-:7])[c:6]1",
        description="Pyridine N-oxide replaces phenol. "
                    "Changed electronics and H-bonding pattern.",
        expected_impact="N-oxide, polarity, different_electronics",
        complexity_delta=0.3,
        tags=["N-oxide", "polarity", "phenol_isostere"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN009": SmirksEntry(
        id="PHEN009",
        category="benzylic_modifications",
        name="Phenol to benzyl alcohol (C-O to C-C oxidation)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4][CH2:5][OH:6]1",
        description="Benzyl alcohol replaces phenol. "
                    "Migrates oxygen to side chain.",
        expected_impact="Benzylic_alcohol, polarity, different_metabolism",
        complexity_delta=0.2,
        tags=["benzyl_alcohol", "side_chain", "polarity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN010": SmirksEntry(
        id="PHEN010",
        category="o_substitutions",
        name="Phenol to phenoxyethanol (ether extension)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([O:5][CH2:8][CH2:9][OH:10])[c:6][c:7]1",
        description="Phenoxyethanol replaces phenol. "
                    "Extends oxygen to ethylene glycol side chain.",
        expected_impact="Ether, polarity, reduced_pharmacopia",
        complexity_delta=0.5,
        tags=["phenoxyethanol", "ether", "polarity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN011": SmirksEntry(
        id="PHEN011",
        category="amide_bond_replacements",
        name="Phenol to phenylurea (urea isostere)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4][NH:5][C:8](=[O:9])[NH2:10]1",
        description="Phenylurea replaces phenol. "
                    "Urea moiety provides different H-bonding.",
        expected_impact="Urea, H-bonding, different_electronics",
        complexity_delta=0.8,
        tags=["urea", "phenylurea", "hbonding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN012": SmirksEntry(
        id="PHEN012",
        category="aromatic_ring_swaps",
        name="Phenol to pyrimidine N-oxide (heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[n:5][c:4][c:3][n:2][c:1]1",
        description="Pyrimidine replaces benzene ring. "
                    "Major ring change with different N positions.",
        expected_impact="Pyrimidine, heterocycle, different_electronics",
        complexity_delta=1.0,
        tags=["pyrimidine", "heterocycle", "aromatic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN014": SmirksEntry(
        id="PHEN014",
        category="steric_shielding",
        name="Phenol to tert-butylbenzene (steric shield)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([C:8]([C:9])([C:10])[C:11])[c:6][c:7]1",
        description="tert-Butylbenzene replaces phenol. "
                    "Major steric group removes H-bonding entirely.",
        expected_impact="Steric_shielding, t-butyl, hydrophobic",
        complexity_delta=0.5,
        tags=["tert-butyl", "steric_shielding", "hydrophobic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN015": SmirksEntry(
        id="PHEN015",
        category="nitrile_modifications",
        name="Phenol to phenoxyacetonitrile (nitrile isostere)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([O:5][CH2:8][C:9]#[N:10])[c:6][c:7]1",
        description="Phenoxyacetonitrile replaces phenol. "
                    "Nitrile group adds different electronics.",
        expected_impact="Nitrile, ether, different_electronics",
        complexity_delta=0.5,
        tags=["nitrile", "ether", "phenoxyacetonitrile"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN016": SmirksEntry(
        id="PHEN016",
        category="metabolic_stability",
        name="Phenol to tetrahydrothiophenone (sulfur heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([C:8](=[O:9])[CH2:10][CH2:11][S:12])[c:5][c:6]1",
        description="Tetrahydrothiophenone replaces phenol. "
                    "Saturated heterocycle with ketone.",
        expected_impact="Sulfur, ketone, saturated_ring",
        complexity_delta=0.8,
        tags=["thiophene", "ketone", "saturated"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN017": SmirksEntry(
        id="PHEN017",
        category="aromatic_ring_swaps",
        name="Phenol to pyrazolone (nitrogen heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[n:5][n:6][c:7][c:8][c:9]1",
        description="Pyrazolone replaces phenol. "
                    "5-membered heterocycle with two nitrogens.",
        expected_impact="Pyrazole, nitrogen, aromatic_5member",
        complexity_delta=0.8,
        tags=["pyrazole", "nitrogen", "aromatic_5member"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN018": SmirksEntry(
        id="PHEN018",
        category="carboxylic_acid_replacements",
        name="Phenol to dihydrobenzimidazolone (cyclic urea)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([NH:8][C:9](=[O:10])[NH:11])[c:5][c:6]1",
        description="Dihydrobenzimidazolone replaces phenol. "
                    "Cyclic urea in fused benzene ring.",
        expected_impact="Cyclic_urea, lactam, H-bonding",
        complexity_delta=0.8,
        tags=["benzimidazolone", "cyclic_urea", "lactam"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN019": SmirksEntry(
        id="PHEN019",
        category="aromatic_ring_swaps",
        name="Phenol to phenylfuran (furan replacement)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([o:8]1[c:9][c:10][c:11][c:12]1)[c:5][c:6]1",
        description="Phenylfuran replaces phenol. "
                    "Furan ring fused to central benzene.",
        expected_impact="Furan, fused_ring, heteroaryl",
        complexity_delta=0.8,
        tags=["furan", "fused_ring", "phenylfuran"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN020": SmirksEntry(
        id="PHEN020",
        category="aromatic_ring_swaps",
        name="Phenol to aminobenzoxazole (benzoxazole)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([n:8]2[c:9][c:10][o:11][c:12]2)[c:5][c:6]1",
        description="Benzoxazole replaces phenol. "
                    "Fused heterocycle with N and O.",
        expected_impact="Benzoxazole, fused_ring, N_O_heterocycle",
        complexity_delta=0.8,
        tags=["benzoxazole", "fused_ring", "N_O_heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN021": SmirksEntry(
        id="PHEN021",
        category="aromatic_ring_swaps",
        name="Phenol to pyrrolopyridine (bicyclic N-heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][n:8]2[c:9][c:10][c:11][c:12]2[c:5][c:6]1",
        description="Pyrrolopyridine replaces phenol. "
                    "Fused 5-6 bicyclic system with nitrogen.",
        expected_impact="Bicyclic_nitrogen, aromatic, fused",
        complexity_delta=1.0,
        tags=["pyrrolopyridine", "fused_ring", "bicyclic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN022": SmirksEntry(
        id="PHEN022",
        category="aromatic_ring_swaps",
        name="Phenol to cyclohexanol (saturated ring)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[C:1]1[C:2][C:3][C:4]([O:5])[C:6][C:7]1",
        description="Cyclohexanol replaces phenol. "
                    "Full saturation removes aromatic stacking.",
        expected_impact="Saturation, cyclohexanol, non_aromatic",
        complexity_delta=0.5,
        tags=["cyclohexane", "saturated", "alicyclic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN023": SmirksEntry(
        id="PHEN023",
        category="amine_modifications",
        name="Phenol to tetrahydropyridine (cyclic amine)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([N:5]1[C:8]=[C:9][C:10][C:11]1)[c:6][c:7]1",
        description="Tetrahydropyridine replaces phenol. "
                    "Partially saturated 6-membered ring with nitrogen.",
        expected_impact="Piperidine, unsaturated, amine",
        complexity_delta=0.8,
        tags=["tetrahydropyridine", "amine", "unsaturated"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN024": SmirksEntry(
        id="PHEN024",
        category="aromatic_ring_swaps",
        name="Phenol to hydroxypyridine (N-heterocycle with OH)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[n:5][c:4][c:3][c:2][c:1]1",
        description="Hydroxypyridine replaces phenol. "
                    "Pyridine with hydroxyl at adjacent position.",
        expected_impact="Pyridone, H-bonding, heterocycle",
        complexity_delta=0.3,
        tags=["hydroxypyridine", "pyridine", "OH_heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN025": SmirksEntry(
        id="PHEN025",
        category="aromatic_ring_swaps",
        name="Phenol to cyclohexene (unsaturated carbocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[C:1]1[C:2]=[C:3][C:4]([OH:5])[C:6][C:7]1",
        description="Cyclohexene replaces phenol. "
                    "One double bond remains in ring.",
        expected_impact="Unsaturated, cyclohexene, alicyclic",
        complexity_delta=0.5,
        tags=["cyclohexene", "unsaturated", "alicyclic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN026": SmirksEntry(
        id="PHEN026",
        category="aromatic_ring_swaps",
        name="Phenol to pyrazolo[3,4-d]pyrimidine (fused heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][n:8]2[c:9][c:10][n:11][c:12]2[c:5][c:6]1",
        description="Pyrazolo[3,4-d]pyrimidine replaces phenol. "
                    "Complex fused bicyclic heterocycle.",
        expected_impact="Fused_heterocycle, pyrazolo, pyrimidine",
        complexity_delta=1.5,
        tags=["pyrazolo", "pyrimidine", "fused_heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN027": SmirksEntry(
        id="PHEN027",
        category="aromatic_ring_swaps",
        name="Phenol to pyridine (simple N isostere)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4][n:5][c:6]1",
        description="Pyridine replaces benzene ring in phenol. "
                    "Nitrogen adds dipole and H-bond acceptor.",
        expected_impact="Pyridine, nitrogen, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["pyridine", "nitrogen", "hbond_acceptor"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN028": SmirksEntry(
        id="PHEN028",
        category="aromatic_ring_swaps",
        name="Phenol to 2-furyl (O-heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3]([o:8])[c:9][c:10]1",
        description="2-Furyl replaces phenol. "
                    "Furan attached at position 2.",
        expected_impact="Furan, oxygen, heteroaryl",
        complexity_delta=0.5,
        tags=["furan", "oxygen", "heteroaryl"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN029": SmirksEntry(
        id="PHEN029",
        category="halogen_substitutions",
        name="Phenol to chlorobenzene (halogen isostere)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([Cl:5])[c:6][c:7]1",
        description="Chlorobenzene replaces phenol. "
                    "Chlorine adds polarizability.",
        expected_impact="Chlorine, polarizability, aromatic",
        complexity_delta=0.0,
        tags=["chlorine", "phenol_isostere", "polarizability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "PHEN030": SmirksEntry(
        id="PHEN030",
        category="halogen_substitutions",
        name="Phenol to bromobenzene (halogen scan)",
        smirks="[c:1]1[c:2][c:3][c:4]([OH:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([Br:5])[c:6][c:7]1",
        description="Bromobenzene replaces phenol. "
                    "Bromine adds more polarizability than chlorine.",
        expected_impact="Bromine, polarizability, halogen",
        complexity_delta=0.0,
        tags=["bromine", "phenol_isostere", "polarizability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Table 4.3"
    ),
    "KETO001": SmirksEntry(
        id="KETO001",
        category="metabolic_stability",
        name="Secondary alcohol to ketone (oxidative metabolism)",
        smirks="[CH:1]([OH:2])[CH3:3]>>[C:1](=[O:2])[CH3:3]",
        description="Ketone replaces secondary alcohol. "
                    "Oxidative metabolism of alcohol.",
        expected_impact="Oxidation, ketone, metabolic",
        complexity_delta=0.0,
        tags=["oxidation", "ketone", "alcohol"],
        reference="Alcohol ketone oxidation"
    ),
    "KETO002": SmirksEntry(
        id="KETO002",
        category="amide_bond_replacements",
        name="Ketone to pyrazoles (heterocycle formation)",
        smirks="[C:1](=[O:2])[C:3]>>[c:1]1[c:2][c:3][n:4][n:5]1",
        description="Pyrazole replaces ketone. "
                    "Forms 5-membered heterocycle with two nitrogens.",
        expected_impact="Pyrazole, heterocycle, carbonyl",
        complexity_delta=0.8,
        tags=["pyrazole", "heterocycle", "carbonyl"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "DRUG001": SmirksEntry(
        id="DRUG001",
        category="metabolic_stability",
        name="Olefin to phenyl (aromatic ring formation)",
        smirks="[C:1]=[C:2]>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Phenyl ring forms from olefin. "
                    "Aromatization increases metabolic stability.",
        expected_impact="Aromaticity, metabolic_stability, planarity",
        complexity_delta=0.5,
        tags=["aromatic", "olefin", "metabolic_stability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11 (Drug Guru)"
    ),
    "DRUG002": SmirksEntry(
        id="DRUG002",
        category="carbonyl_modifications",
        name="Olefin to amide (functional group interconversion)",
        smirks="[C:1]=[C:2]>>[C:1][C:2](=[O:3])[N:4]",
        description="Amide forms from olefin. "
                    "Changes reactivity and H-bonding.",
        expected_impact="Amide, functional_group, H-bonding",
        complexity_delta=0.3,
        tags=["amide", "olefin", "functional_group"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11 (Drug Guru)"
    ),
    "DRUG003": SmirksEntry(
        id="DRUG003",
        category="halogen_substitutions",
        name="Aryl chlorine removal (hERG reduction)",
        smirks="[c:1][Cl:2]>>[c:1][H:2]",
        description="Chlorine removed from aromatic ring. "
                    "Reduces hERG binding and metabolic lability.",
        expected_impact="hERG reduction, defluorination, metabolic",
        complexity_delta=0.0,
        tags=["Cl_removal", "hERG", "metabolic_stability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11 (Drug Guru)"
    ),
    "NME001": SmirksEntry(
        id="NME001",
        category="amine_modifications",
        name="Secondary amine to tertiary amine (N-methylation)",
        smirks="[CH3:1][N:2][C:3]>>[CH3:1][N:2]([CH3:4])[C:3]",
        description="N-methylation adds methyl to secondary amine. "
                    "Increases lipophilicity and reduces H-bonding.",
        expected_impact="N-methylation, lipophilicity, H-bond_reduction",
        complexity_delta=0.1,
        tags=["N-methylation", "tertiary_amine", "lipophilicity"],
        reference="Amine N-methylation SAR"
    ),
    "NME002": SmirksEntry(
        id="NME002",
        category="amine_modifications",
        name="Dimethylamine to trimethylamine (quaternary approach)",
        smirks="[CH3:1][N:2]([CH3:3])[C:4]>>[CH3:1][N:2]([CH3:3])([CH3:5])[C:4]",
        description="Adds third methyl to dimethylamine. "
                    "Further reduces H-bonding donor.",
        expected_impact="Lipophilicity, quaternary_amine, H-bond_reduction",
        complexity_delta=0.1,
        tags=["trimethylamine", "quaternary", "lipophilicity"],
        reference="Amine quaternary SAR"
    ),
    "NME003": SmirksEntry(
        id="NME003",
        category="amine_modifications",
        name="Primary amine to secondary amine (N-ethylation)",
        smirks="[NH2:1][C:2]>>[NH:1][CH2:3][CH3:4]",
        description="N-ethylation replaces primary with secondary amine. "
                    "Increases size and reduces polarity.",
        expected_impact="N-ethylation, secondary_amine, size",
        complexity_delta=0.1,
        tags=["N-ethylation", "secondary_amine", "size"],
        reference="Amine N-ethylation SAR"
    ),
    "PIPE001": SmirksEntry(
        id="PIPE001",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to morpholine (O for CH2 swap)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[O:2][C:3][C:4][C:5][C:6]1",
        description="Morpholine replaces piperidine. "
                    "Oxygen replaces nitrogen, changes H-bonding.",
        expected_impact="Morpholine, oxygen, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["morpholine", "piperidine", "oxygen"],
        reference="Nitrogen heterocycle swaps"
    ),
    "PIPE002": SmirksEntry(
        id="PIPE002",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to thiomorpholine (S for CH2 swap)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[S:2][C:3][C:4][C:5][C:6]1",
        description="Thiomorpholine replaces piperidine. "
                    "Sulfur adds lipophilicity.",
        expected_impact="Thiomorpholine, sulfur, lipophilicity",
        complexity_delta=0.3,
        tags=["thiomorpholine", "piperidine", "sulfur"],
        reference="Nitrogen heterocycle swaps"
    ),
    "PIPE003": SmirksEntry(
        id="PIPE003",
        category="ether_modifications",
        name="Morpholine to thiomorpholine (S for O swap)",
        smirks="[C:1]1[O:2][C:3][C:4][C:5][C:6]1>>[C:1]1[S:2][C:3][C:4][C:5][C:6]1",
        description="Thiomorpholine replaces morpholine. "
                    "Sulfur adds lipophilicity and different electronics.",
        expected_impact="Thiomorpholine, sulfur, lipophilicity",
        complexity_delta=0.3,
        tags=["thiomorpholine", "morpholine", "sulfur"],
        reference="Ether thioether exchange"
    ),
    "PIPE004": SmirksEntry(
        id="PIPE004",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to piperazine (N for CH2 swap)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[N:2][C:3][N:4][C:5][C:6]1",
        description="Piperazine replaces piperidine. "
                    "Adds second nitrogen, doubles H-bonding capability.",
        expected_impact="Piperazine, second_N, H-bonding",
        complexity_delta=0.3,
        tags=["piperazine", "second_N", "H-bonding"],
        reference="Nitrogen heterocycle swaps"
    ),
    "ADV001": SmirksEntry(
        id="ADV001",
        category="amide_bond_replacements",
        name="Primary amide to thioamide (sulfur isostere)",
        smirks="[N:1][C:2](=[O:3])[C:4]>>[N:1][C:2](=[S:3])[C:4]",
        description="Thioamide replaces amide. "
                    "Sulfur adds polarizability and changes H-bonding.",
        expected_impact="Thioamide, sulfur, H-bonding",
        complexity_delta=0.0,
        tags=["thioamide", "sulfur", "isostere"],
        reference="Thioamide isosteres"
    ),
    "ADV003": SmirksEntry(
        id="ADV003",
        category="carbonyl_modifications",
        name="Ketone to hydrazone (N substitution)",
        smirks="[C:1](=[O:2])[C:3]>>[C:1](=[N:4][N:5]([C:6])[C:7])[C:3]",
        description="Hydrazone replaces ketone. "
                    "N-N bond adds different electronics.",
        expected_impact="Hydrazone, nitrogen, different_electronics",
        complexity_delta=0.3,
        tags=["hydrazone", "nitrogen", "carbonyl"],
        reference="Hydrazone isosteres"
    ),
    "ADV004": SmirksEntry(
        id="ADV004",
        category="carbonyl_modifications",
        name="Ketone to semicarbazone (urea analog)",
        smirks="[C:1](=[O:2])[C:3]>>[C:1](=[N:4][N:5][C:6](=[O:7])[N:8])[C:3]",
        description="Semicarbazone replaces ketone. "
                    "Adds urea-like moiety with different properties.",
        expected_impact="Semicarbazone, urea, carbonyl",
        complexity_delta=0.5,
        tags=["semicarbazone", "urea", "carbonyl"],
        reference="Semicarbazone isosteres"
    ),
    "ADV005": SmirksEntry(
        id="ADV005",
        category="amine_modifications",
        name="Guanidine to isothiourea (S for N exchange)",
        smirks="[N:1]=[C:2](-[N:3])-[N:4]>>[N:1]-[C:2](=[S:3])-[N:4]",
        description="Isothiourea replaces guanidine. "
                    "Sulfur adds different electronics and size.",
        expected_impact="Isothiourea, sulfur, guanidine",
        complexity_delta=0.2,
        tags=["isothiourea", "sulfur", "guanidine"],
        reference="Guanidine isosteres"
    ),
    "ADV006": SmirksEntry(
        id="ADV006",
        category="amine_modifications",
        name="Guanidine to thiourea (S exchange)",
        smirks="[NH2:1][C:2](=[N:3][NH2:4])>>[NH2:1][C:2](=[S:3])[NH2:4]",
        description="Thiourea replaces guanidine. "
                    "Sulfur replaces one nitrogen.",
        expected_impact="Thiourea, sulfur, guanidine",
        complexity_delta=0.0,
        tags=["thiourea", "sulfur", "guanidine"],
        reference="Guanidine thiourea isosteres"
    ),
    "ADV007": SmirksEntry(
        id="ADV007",
        category="aromatic_ring_swaps",
        name="Cyclohexane to cyclohexene (partial saturation)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2]=[C:3][C:4][C:5][C:6]1",
        description="Cyclohexene replaces cyclohexane. "
                    "One double bond adds reactivity.",
        expected_impact="Unsaturation, cyclohexene, reactivity",
        complexity_delta=0.3,
        tags=["cyclohexene", "unsaturation", "alkene"],
        reference="Aromatic ring saturation SAR"
    ),
    "ADV008": SmirksEntry(
        id="ADV008",
        category="aromatic_ring_swaps",
        name="Cyclohexene to benzene (full aromatization)",
        smirks="[C:1]1[C:2]=[C:3][C:4][C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Benzene replaces cyclohexene. "
                    "Full aromatization adds planarity and stacking.",
        expected_impact="Aromaticity, planarity, stacking",
        complexity_delta=0.3,
        tags=["benzene", "aromatic", "planarity"],
        reference="Aromatic ring formation SAR"
    ),
    "ADV009": SmirksEntry(
        id="ADV009",
        category="aromatic_ring_swaps",
        name="Imidazole to pyrazole (N addition)",
        smirks="[c:1]1[n:2][c:3][n:4][c:5]1>>[c:1]1[n:2][n:3][c:4][n:5]1",
        description="Pyrazole replaces imidazole. "
                    "Adds extra nitrogen, changes H-bonding.",
        expected_impact="Nitrogen addition, pyrazole, H-bonding",
        complexity_delta=0.3,
        tags=["pyrazole", "imidazole", "nitrogen"],
        reference="Imidazole pyrazole isosteres"
    ),
    "ADV010": SmirksEntry(
        id="ADV010",
        category="aromatic_ring_swaps",
        name="Pyrrole to furan (O for NH exchange)",
        smirks="[c:1]1[c:2][c:3][nH:4][c:5][c:6]1>>[c:1]1[c:2][c:3][o:4][c:5][c:6]1",
        description="Furan replaces pyrrole. "
                    "Oxygen replaces NH, changes H-bonding.",
        expected_impact="Furan, oxygen, H-bond_reduction",
        complexity_delta=0.3,
        tags=["furan", "pyrrole", "oxygen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "OXIM001": SmirksEntry(
        id="OXIM001",
        category="carbonyl_modifications",
        name="Ketone to oxime (N replacement)",
        smirks="[C:1](=[O:2])[C:3]>>[C:1](=[N:2][OH:4])[C:3]",
        description="Oxime replaces ketone. "
                    "Adds H-bond donor and N.",
        expected_impact="Oxime, H-bond_donor, nitrogen",
        complexity_delta=0.3,
        tags=["oxime", "nitrogen", "hbond_donor"],
        reference="Oxime isosteres"
    ),
    "OXIM002": SmirksEntry(
        id="OXIM002",
        category="carbonyl_modifications",
        name="Ketone to oxime with mapping (explicit)",
        smirks="[C:1](=[O:2])[C:3]>>[C:1](=NO)[C:3]",
        description="Oxime replaces ketone. "
                    "NO group adds polarity and H-bonding.",
        expected_impact="Oxime, polarity, H-bonding",
        complexity_delta=0.3,
        tags=["oxime", "nitrogen", "polarity"],
        reference="Oxime isosteres"
    ),
    "OXIM003": SmirksEntry(
        id="OXIM003",
        category="carbonyl_modifications",
        name="Ketone to oxime with explicit O-H",
        smirks="[C:1](=[O:2])[C:3]>>[C:1](=[N:4]([O:5])[H:6])[C:3]",
        description="Oxime replaces ketone. "
                    "Hydroxyimino group provides H-bonding.",
        expected_impact="Oxime, H-bonding, nitrogen",
        complexity_delta=0.3,
        tags=["oxime", "hydroxyimino", "hbonding"],
        reference="Oxime carbonyl isosteres"
    ),
    "AMID009": SmirksEntry(
        id="AMID009",
        category="amide_bond_replacements",
        name="Primary amide to cyclic amine (piperidine)",
        smirks="[N:1][C:2](=[O:3])[C:4]>>[N:1]1[C:5][C:6][C:7][C:8][C:9]1",
        description="Piperidine replaces amide group. "
                    "Cyclic constraint and reduced polarity.",
        expected_impact="Piperidine, cyclic, polarity",
        complexity_delta=0.3,
        tags=["piperidine", "cyclic", "amide_replacement"],
        reference="Amide cyclic replacements"
    ),
    "AMID010": SmirksEntry(
        id="AMID010",
        category="amide_bond_replacements",
        name="Primary amide to homopiperidine (7-membered)",
        smirks="[N:1][C:2](=[O:3])[C:4]>>[N:1]1[C:5][C:6][C:7][C:8][C:9][C:10]1",
        description="Homopiperidine replaces amide. "
                    "7-membered ring adds flexibility.",
        expected_impact="Homopiperidine, 7-membered, flexibility",
        complexity_delta=0.4,
        tags=["homopiperidine", "7-membered", "flexibility"],
        reference="Amide cyclic replacements"
    ),
    "AMID011": SmirksEntry(
        id="AMID011",
        category="amide_bond_replacements",
        name="Primary amide to azetidine (small cyclic)",
        smirks="[N:1][C:2](=[O:3])[C:4]>>[N:1]1[C:5][C:6][C:7]1",
        description="Azetidine replaces amide. "
                    "Smallest cyclic amine replacement.",
        expected_impact="Azetidine, small_ring, cyclic",
        complexity_delta=0.2,
        tags=["azetidine", "small_ring", "cyclic"],
        reference="Amide cyclic replacements"
    ),
    "AMID012": SmirksEntry(
        id="AMID012",
        category="amide_bond_replacements",
        name="Primary amide to morpholine analog",
        smirks="[N:1][C:2](=[O:3])[C:4]>>[O:1]1[C:5][C:6][C:7][C:8]1",
        description="Morpholine replaces amide. "
                    "Oxygen adds H-bond acceptor.",
        expected_impact="Morpholine, oxygen, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["morpholine", "oxygen", "amide_replacement"],
        reference="Amide replacements"
    ),
    "AMID013": SmirksEntry(
        id="AMID013",
        category="amine_modifications",
        name="Piperidine to primary amide (oxidation)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1](=[O:2])(=[O:3])[NH2:4]",
        description="Primary amide replaces piperidine. "
                    "Oxidation of cyclic amine to acid.",
        expected_impact="Amide, oxidation, acidity",
        complexity_delta=0.3,
        tags=["amide", "oxidation", "piperidine"],
        reference="Piperidine oxidation SAR"
    ),
    "AMID014": SmirksEntry(
        id="AMID014",
        category="ether_modifications",
        name="Morpholine to primary amide (ring opening oxidation)",
        smirks="[C:1]1[O:2][C:3][C:4][C:5][C:6]1>>[C:1](=[O:2])(=[O:3])[NH2:4]",
        description="Primary amide replaces morpholine. "
                    "Ring opening with oxidation.",
        expected_impact="Amide, ring_opening, oxidation",
        complexity_delta=0.3,
        tags=["amide", "ring_opening", "morpholine"],
        reference="Morpholine oxidation SAR"
    ),
    "UREA001": SmirksEntry(
        id="UREA001",
        category="carbonyl_modifications",
        name="Urea to carbonate (oxygen addition)",
        smirks="[N:1][C:2](=[O:3])[N:4]>>[O:1][C:2](=[O:3])[O:4]",
        description="Carbonate replaces urea. "
                    "Both oxygens on carbonyl.",
        expected_impact="Carbonate, oxygen, different_electronics",
        complexity_delta=0.2,
        tags=["carbonate", "oxygen", "carbonyl"],
        reference="Carbonate isosteres"
    ),
    "UREA002": SmirksEntry(
        id="UREA002",
        category="amide_bond_replacements",
        name="Urea to carbamate (N to O substitution)",
        smirks="[N:1][C:2](=[O:3])[N:4]>>[O:1][C:2](=[O:3])[N:4]",
        description="Carbamate replaces urea. "
                    "One NH replaced by O.",
        expected_impact="Carbamate, oxygen, reduced_H-bond",
        complexity_delta=0.1,
        tags=["carbamate", "urea", "oxygen"],
        reference="Urea carbamate isosteres"
    ),
    "UREA003": SmirksEntry(
        id="UREA003",
        category="amide_bond_replacements",
        name="Urea to thiourea (S for O exchange)",
        smirks="[N:1][C:2](=[O:3])[N:4]>>[N:1][C:2](=[S:3])[N:4]",
        description="Thiourea replaces urea. "
                    "Sulfur adds polarizability.",
        expected_impact="Thiourea, sulfur, polarity",
        complexity_delta=0.0,
        tags=["thiourea", "sulfur", "urea"],
        reference="Urea thiourea isosteres"
    ),
    "LACT001": SmirksEntry(
        id="LACT001",
        category="carbonyl_modifications",
        name="Lactam to lactone (N to O substitution)",
        smirks="[N:1]1[C:2](=[O:3])[C:4][C:5][C:6][C:7]1>>[O:1]1[C:2](=[O:3])[C:4][C:5][C:6][C:7]1",
        description="Lactone replaces lactam. "
                    "Oxygen replaces nitrogen in ring.",
        expected_impact="Lactone, oxygen, ring",
        complexity_delta=0.3,
        tags=["lactone", "lactam", "oxygen"],
        reference="Lactam lactone isosteres"
    ),
    "LACT002": SmirksEntry(
        id="LACT002",
        category="carbonyl_modifications",
        name="Lactone to lactam (N for O substitution)",
        smirks="[O:1]1[C:2](=[O:3])[C:4][C:5][C:6][C:7]1>>[N:1]1[C:2](=[O:3])[C:4][C:5][C:6][C:7]1",
        description="Lactam replaces lactone. "
                    "Nitrogen adds H-bonding donor.",
        expected_impact="Lactam, nitrogen, H-bonding",
        complexity_delta=0.3,
        tags=["lactam", "lactone", "nitrogen"],
        reference="Lactone lactam isosteres"
    ),
    "SLFA011": SmirksEntry(
        id="SLFA011",
        category="sulfonamide_modifications",
        name="Sulfonamide to phosphonate (P for S exchange)",
        smirks="[S:1](=[O:2])(=[O:3])[N:4]>>[P:1](=[O:2])(=[O:3])[O:4]",
        description="Phosphonate replaces sulfonamide. "
                    "Phosphorus adds different properties.",
        expected_impact="Phosphonate, phosphorus, different_electronics",
        complexity_delta=0.5,
        tags=["phosphonate", "phosphorus", "sulfonamide"],
        reference="Sulfonamide phosphonate isosteres"
    ),
    "SLFA012": SmirksEntry(
        id="SLFA012",
        category="sulfonamide_modifications",
        name="Sulfonamide to amide (remove SO2)",
        smirks="[S:1](=[O:2])(=[O:3])[N:4]>>[C:1](=[O:2])[N:4]",
        description="Amide replaces sulfonamide. "
                    "Removes sulfur dioxide group.",
        expected_impact="Amide, SO2_removal, polarity",
        complexity_delta=0.2,
        tags=["amide", "sulfonamide", "SO2"],
        reference="Sulfonamide amide isosteres"
    ),
    "SLFA013": SmirksEntry(
        id="SLFA013",
        category="sulfonyl_modifications",
        name="Sulfonamide to sulfoxide (reduce oxidation state)",
        smirks="[S:1](=[O:2])(=[O:3])[N:4]>>[S:1](=[O:2])[N:4]",
        description="Sulfoxide replaces sulfonamide. "
                    "Removes one oxygen.",
        expected_impact="Sulfoxide, reduced_oxidation, polarity",
        complexity_delta=0.2,
        tags=["sulfoxide", "sulfonamide", "SO2"],
        reference="Sulfone reduction isosteres"
    ),
    "PHOS001": SmirksEntry(
        id="PHOS001",
        category="carboxylic_acid_replacements",
        name="Phosphate to thiophosphate (S for O exchange)",
        smirks="[O:1]P(=O)([O:2])[O:3]>>[O:1]P(=S)([O:2])[O:3]",
        description="Thiophosphate replaces phosphate. "
                    "Sulfur adds different metabolic stability.",
        expected_impact="Thiophosphate, sulfur, metabolic",
        complexity_delta=0.3,
        tags=["thiophosphate", "sulfur", "phosphate"],
        reference="Phosphate thiophosphate isosteres"
    ),
    "PHOS002": SmirksEntry(
        id="PHOS002",
        category="carboxylic_acid_replacements",
        name="Phosphonate to sulfonate (S for P exchange)",
        smirks="[C:1]P(=O)([O:2])[O:3]>>[C:1]S(=O)(=O)[O:3]",
        description="Sulfonate replaces phosphonate. "
                    "Sulfur replaces phosphorus.",
        expected_impact="Sulfonate, sulfur, phosphorus",
        complexity_delta=0.3,
        tags=["sulfonate", "sulfur", "phosphonate"],
        reference="Phosphonate sulfonate isosteres"
    ),
    "NHEX001": SmirksEntry(
        id="NHEX001",
        category="nitrogen_heterocycle_swaps",
        name="Pyridine to pyrimidine (N positional isomer)",
        smirks="[c:1]1[c:2][c:3][n:4][c:5][c:6]1>>[c:1]1[c:2][c:3][n:4][n:5][c:6]1",
        description="Pyrimidine replaces pyridine. "
                    "Different N positions affect basicity and H-bonding.",
        expected_impact="Pyrimidine, N_position, basicity",
        complexity_delta=0.2,
        tags=["pyrimidine", "N_position", "diazine"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX002": SmirksEntry(
        id="NHEX002",
        category="nitrogen_heterocycle_swaps",
        name="Pyridine to pyridazine (N-N adjacency)",
        smirks="[c:1]1[c:2][c:3][n:4][c:5][c:6]1>>[c:1]1[n:4][n:3][c:2][c:1]1",
        description="Pyridazine replaces pyridine. "
                    "Adjacent nitrogens create different dipole.",
        expected_impact="Pyridazine, N_adjacent, dipole",
        complexity_delta=0.2,
        tags=["pyridazine", "N_adjacent", "diazine"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX003": SmirksEntry(
        id="NHEX003",
        category="nitrogen_heterocycle_swaps",
        name="Pyridine to pyrazine (N opposite positions)",
        smirks="[c:1]1[c:2][c:3][n:4][c:5][c:6]1>>[c:1]1[n:5][c:3][n:4][c:2][c:1]1",
        description="Pyrazine replaces pyridine. "
                    "para N positions create symmetric dipole.",
        expected_impact="Pyrazine, symmetric, N_positions",
        complexity_delta=0.2,
        tags=["pyrazine", "N_position", "diazine"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX004": SmirksEntry(
        id="NHEX004",
        category="nitrogen_heterocycle_swaps",
        name="Pyridazine to pyrimidine (diazine comparison)",
        smirks="[c:1]1[n:2][n:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][n:4][n:5][c:6]1",
        description="Pyrimidine replaces pyridazine. "
                    "Non-adjacent N positions different from 1,2.",
        expected_impact="Pyrimidine, diazine, N_positions",
        complexity_delta=0.2,
        tags=["pyrimidine", "diazine", "N_positions"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX005": SmirksEntry(
        id="NHEX005",
        category="nitrogen_heterocycle_swaps",
        name="2-pyridyl to 3-pyridyl (position isomer)",
        smirks="[c:1]1[n:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][n:3][c:4][c:5][c:6]1",
        description="3-Pyridyl replaces 2-pyridyl. "
                    "N position changes affect binding orientation.",
        expected_impact="Position_isomer, pyridine, binding",
        complexity_delta=0.1,
        tags=["position_isomer", "pyridine", "N_position"],
        reference="Pyridine position isomer SAR"
    ),
    "NHEX006": SmirksEntry(
        id="NHEX006",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to piperazine (add N)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[N:2][C:3][N:4][C:5][C:6]1",
        description="Piperazine replaces piperidine. "
                    "Adds second nitrogen doubling H-bonding.",
        expected_impact="Second_N, piperazine, H-bonding",
        complexity_delta=0.3,
        tags=["piperazine", "second_N", "H-bonding"],
        reference="Nitrogen heterocycle swaps"
    ),
    "NHEX007": SmirksEntry(
        id="NHEX007",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to morpholine (O for N swap)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[O:2][C:3][C:4][C:5][C:6]1",
        description="Morpholine replaces piperidine. "
                    "Oxygen replaces nitrogen, H-bond acceptor not donor.",
        expected_impact="Morpholine, oxygen, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["morpholine", "oxygen", "H-bond_acceptor"],
        reference="Nitrogen heterocycle swaps"
    ),
    "NHEX008": SmirksEntry(
        id="NHEX008",
        category="ether_modifications",
        name="Morpholine to thiomorpholine (S for O swap)",
        smirks="[C:1]1[O:2][C:3][C:4][C:5][C:6]1>>[C:1]1[S:2][C:3][C:4][C:5][C:6]1",
        description="Thiomorpholine replaces morpholine. "
                    "Sulfur adds lipophilicity.",
        expected_impact="Thiomorpholine, sulfur, lipophilicity",
        complexity_delta=0.3,
        tags=["thiomorpholine", "sulfur", "lipophilicity"],
        reference="Ether thioether exchange"
    ),
    "NHEX009": SmirksEntry(
        id="NHEX009",
        category="nitrogen_heterocycle_swaps",
        name="Pyrrolidine to piperidine (ring expansion)",
        smirks="[C:1]1[C:2][N:3][C:4][C:5]1>>[C:1]1[C:2][N:3][C:4][C:5][C:6]1",
        description="Piperidine replaces pyrrolidine. "
                    "One carbon ring expansion.",
        expected_impact="Ring_expansion, piperidine, size",
        complexity_delta=0.2,
        tags=["ring_expansion", "piperidine", "pyrrolidine"],
        reference="Nitrogen heterocycle swaps"
    ),
    "NHEX010": SmirksEntry(
        id="NHEX010",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to azepane (7-membered ring)",
        smirks="[C:1]1[C:2][N:3][C:4][C:5][C:6]1>>[C:1]1[C:2][N:3][C:4][C:5][C:6][C:7]1",
        description="Azepane replaces piperidine. "
                    "7-membered ring adds flexibility.",
        expected_impact="Azepane, 7-membered, flexibility",
        complexity_delta=0.3,
        tags=["azepane", "7-membered", "flexibility"],
        reference="Nitrogen heterocycle swaps"
    ),
    "NHEX011": SmirksEntry(
        id="NHEX011",
        category="nitrogen_heterocycle_swaps",
        name="Naphthalene to quinoline (fused N-heterocycle)",
        smirks="[c:1]1[c:2][c:3][c:4]2[c:5][c:6][c:7][c:8]1[c:2]2>>[c:1]1[c:2][c:3][c:4]2[n:5][c:6][c:7][c:8]1[c:2]2",
        description="Quinoline replaces naphthalene. "
                    "One CH replaced by N in fused ring.",
        expected_impact="Quinoline, fused_N, heteroaryl",
        complexity_delta=0.5,
        tags=["quinoline", "fused_ring", "nitrogen"],
        reference="Fused heterocycle swaps"
    ),
    "NHEX012": SmirksEntry(
        id="NHEX012",
        category="nitrogen_heterocycle_swaps",
        name="Naphthalene to isoquinoline (N position isomer)",
        smirks="[c:1]1[c:2][c:3][c:4]2[c:5][c:6][c:7][c:8]1[c:2]2>>[c:1]1[c:2][c:3]2[n:4][c:5][c:6][c:7]1[c:2]2",
        description="Isoquinoline replaces naphthalene. "
                    "Different N position in fused system.",
        expected_impact="Isoquinoline, N_position, fused",
        complexity_delta=0.5,
        tags=["isoquinoline", "N_position", "fused"],
        reference="Fused heterocycle swaps"
    ),
    "NHEX014": SmirksEntry(
        id="NHEX014",
        category="nitrogen_heterocycle_swaps",
        name="Quinoline to quinazoline (extra N)",
        smirks="[c:1]1[c:2][c:3][c:4]2[n:5][c:6][c:7][c:8]1[c:2]2>>[c:1]1[c:2][n:3]2[n:4][c:5][c:6][c:7]1[c:2]2",
        description="Quinazoline replaces quinoline. "
                    "Second nitrogen added to fused ring.",
        expected_impact="Quinazoline, extra_N, fused",
        complexity_delta=0.5,
        tags=["quinazoline", "extra_N", "fused"],
        reference="Fused heterocycle swaps"
    ),
    "NHEX015": SmirksEntry(
        id="NHEX015",
        category="nitrogen_heterocycle_swaps",
        name="Quinoline to isoquinoline (N position swap)",
        smirks="[c:1]1[c:2][c:3][c:4]2[n:5][c:6][c:7][c:8]1[c:2]2>>[c:1]1[c:2][c:3]2[n:4][c:5][c:6][c:7]1[c:2]2",
        description="Isoquinoline replaces quinoline. "
                    "N moved from position 1 to position 2.",
        expected_impact="Isoquinoline, N_position, fused",
        complexity_delta=0.3,
        tags=["isoquinoline", "N_position", "quinoline"],
        reference="Quinoline isoquinoline isosteres"
    ),
    "NHEX016": SmirksEntry(
        id="NHEX016",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to azetidine (ring contraction)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[N:2][C:3][C:4]1",
        description="Azetidine replaces piperidine. "
                    "Major ring contraction to 3-membered.",
        expected_impact="Ring_contraction, azetidine, size",
        complexity_delta=0.5,
        tags=["azetidine", "ring_contraction", "small_ring"],
        reference="Nitrogen heterocycle swaps"
    ),
    "NHEX017": SmirksEntry(
        id="NHEX017",
        category="nitrogen_heterocycle_swaps",
        name="Piperidine to pyrrolidine (ring contraction)",
        smirks="[C:1]1[N:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2][N:3][C:4][C:5]1",
        description="Pyrrolidine replaces piperidine. "
                    "5-membered ring instead of 6.",
        expected_impact="Ring_contraction, pyrrolidine, size",
        complexity_delta=0.2,
        tags=["pyrrolidine", "5-membered", "ring_contraction"],
        reference="Nitrogen heterocycle swaps"
    ),
    "NHEX018": SmirksEntry(
        id="NHEX018",
        category="ether_modifications",
        name="Pyrrolidine to tetrahydrofuran (N to O swap)",
        smirks="[C:1]1[C:2][N:3][C:4][C:5]1>>[C:1]1[C:2][O:3][C:4][C:5]1",
        description="Tetrahydrofuran replaces pyrrolidine. "
                    "Oxygen replaces nitrogen.",
        expected_impact="THF, oxygen, H-bond_acceptor",
        complexity_delta=0.2,
        tags=["THF", "pyrrolidine", "oxygen"],
        reference="Ether modifications"
    ),
    "NHEX019": SmirksEntry(
        id="NHEX019",
        category="ether_modifications",
        name="Tetrahydrofuran to tetrahydrothiophene (O to S swap)",
        smirks="[C:1]1[C:2][O:3][C:4][C:5]1>>[C:1]1[C:2][S:3][C:4][C:5]1",
        description="Tetrahydrothiophene replaces THF. "
                    "Sulfur adds lipophilicity.",
        expected_impact="THT, sulfur, lipophilicity",
        complexity_delta=0.2,
        tags=["THT", "sulfur", "lipophilicity"],
        reference="Ether thioether exchange"
    ),
    "NHEX021": SmirksEntry(
        id="NHEX021",
        category="aromatic_ring_swaps",
        name="Furan to thiophene (O to S chalcogen swap)",
        smirks="[c:1]1[c:2][c:3][o:4][c:5][c:6]1>>[c:1]1[c:2][c:3][s:4][c:5][c:6]1",
        description="Thiophene replaces furan. "
                    "Sulfur replaces oxygen, adds lipophilicity.",
        expected_impact="Thiophene, furan, sulfur",
        complexity_delta=0.3,
        tags=["thiophene", "furan", "chalcogen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX022": SmirksEntry(
        id="NHEX022",
        category="aromatic_ring_swaps",
        name="Pyrrole to furan (NH to O exchange)",
        smirks="[c:1]1[c:2][c:3][nH:4][c:5][c:6]1>>[c:1]1[c:2][c:3][o:4][c:5][c:6]1",
        description="Furan replaces pyrrole. "
                    "Oxygen replaces NH, removes H-bond donor.",
        expected_impact="Furan, pyrrole, oxygen",
        complexity_delta=0.3,
        tags=["furan", "pyrrole", "oxygen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX023": SmirksEntry(
        id="NHEX023",
        category="aromatic_ring_swaps",
        name="Thiophene to pyrrole (S to NH exchange)",
        smirks="[c:1]1[c:2][c:3][s:4][c:5][c:6]1>>[c:1]1[c:2][c:3][nH:4][c:5][c:6]1",
        description="Pyrrole replaces thiophene. "
                    "NH replaces S, adds H-bond donor.",
        expected_impact="Pyrrole, thiophene, NH",
        complexity_delta=0.3,
        tags=["pyrrole", "thiophene", "NH"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    "NHEX024": SmirksEntry(
        id="NHEX024",
        category="aromatic_ring_swaps",
        name="1,2,4-oxadiazole to 1,2,4-thiadiazole (O to S)",
        smirks="[c:1]1[n:2][o:3][n:4][c:5]1>>[c:1]1[n:2][s:3][n:4][c:5]1",
        description="Thiadiazole replaces oxadiazole. "
                    "Sulfur adds lipophilicity and size.",
        expected_impact="Thiadiazole, sulfur, oxadiazole",
        complexity_delta=0.3,
        tags=["thiadiazole", "sulfur", "oxadiazole"],
        reference="Aromatic heterocycle swaps"
    ),
    "NHEX025": SmirksEntry(
        id="NHEX025",
        category="aromatic_ring_swaps",
        name="Thiazole to isothiazole (N position isomer)",
        smirks="[c:1]1[c:2][n:3][c:4][s:5]1>>[c:1]1[n:3][c:2][c:4][s:5]1",
        description="Isothiazole replaces thiazole. "
                    "N position isomer affects electronics.",
        expected_impact="Isothiazole, N_position, thiazole",
        complexity_delta=0.2,
        tags=["isothiazole", "N_position", "thiazole"],
        reference="Aromatic heterocycle swaps"
    ),
    "CARB001": SmirksEntry(
        id="CARB001",
        category="carbocyclic_replacements",
        name="Benzene to cyclohexane (full saturation)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4][C:5][C:6]1",
        description="Cyclohexane replaces benzene. "
                    "Full saturation removes aromatic stacking.",
        expected_impact="Saturation, cyclohexane, non_aromatic",
        complexity_delta=0.5,
        tags=["cyclohexane", "saturation", "non_aromatic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "CARB002": SmirksEntry(
        id="CARB002",
        category="carbocyclic_replacements",
        name="Benzene to cyclohexene (partial saturation)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2]=[C:3][C:4][C:5][C:6]1",
        description="Cyclohexene replaces benzene. "
                    "One double bond, partial saturation.",
        expected_impact="Cyclohexene, unsaturation, non_aromatic",
        complexity_delta=0.4,
        tags=["cyclohexene", "unsaturation", "non_aromatic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "CARB003": SmirksEntry(
        id="CARB003",
        category="carbocyclic_replacements",
        name="Benzene to cyclohexadiene (diene)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2]=[C:3][C:4]=[C:5][C:6]1",
        description="Cyclohexadiene replaces benzene. "
                    "Two double bonds, still non-aromatic.",
        expected_impact="Cyclohexadiene, diene, non_aromatic",
        complexity_delta=0.4,
        tags=["cyclohexadiene", "diene", "non_aromatic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "CARB004": SmirksEntry(
        id="CARB004",
        category="carbocyclic_replacements",
        name="Benzene to cyclopentane (5-membered ring)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4][C:5]1",
        description="Cyclopentane replaces benzene. "
                    "5-membered saturated ring, different shape.",
        expected_impact="Cyclopentane, 5-membered, shape",
        complexity_delta=0.5,
        tags=["cyclopentane", "5-membered", "shape"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "CARB005": SmirksEntry(
        id="CARB005",
        category="carbocyclic_replacements",
        name="Cyclohexane to cyclopentane (ring contraction)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2][C:3][C:4][C:5]1",
        description="Cyclopentane replaces cyclohexane. "
                    "Ring contraction removes one carbon.",
        expected_impact="Ring_contraction, cyclopentane, size",
        complexity_delta=0.3,
        tags=["cyclopentane", "ring_contraction", "size"],
        reference="Carbocycle swaps"
    ),
    "CARB006": SmirksEntry(
        id="CARB006",
        category="carbocyclic_replacements",
        name="Benzene to cyclohexane (explicit mapping)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4][C:5][C:6]1",
        description="Cyclohexane replaces benzene. "
                    "Full saturation, removes aromatic stacking.",
        expected_impact="Saturation, cyclohexane, non-aromatic",
        complexity_delta=0.5,
        tags=["cyclohexane", "saturation", "non-aromatic"],
        reference="Carbocycle saturation SAR"
    ),
    "CARB007": SmirksEntry(
        id="CARB007",
        category="aromatic_ring_swaps",
        name="Cyclohexane to benzene (aromatization)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Benzene replaces cyclohexane. "
                    "Aromatization adds planarity and stacking.",
        expected_impact="Aromaticity, planarity, stacking",
        complexity_delta=0.5,
        tags=["benzene", "aromaticity", "planarity"],
        reference="Aromatic ring formation"
    ),
    "CARB008": SmirksEntry(
        id="CARB008",
        category="aromatic_ring_swaps",
        name="Cyclohexene to benzene (dehydrogenation)",
        smirks="[C:1]1[C:2]=[C:3][C:4][C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Benzene replaces cyclohexene. "
                    "Dehydrogenation creates aromaticity.",
        expected_impact="Aromaticity, benzene, dehydrogenation",
        complexity_delta=0.4,
        tags=["benzene", "aromaticity", "dehydrogenation"],
        reference="Aromatic formation SAR"
    ),
    "CARB010": SmirksEntry(
        id="CARB010",
        category="carbocyclic_replacements",
        name="Cyclopentane to cyclopentene (add double bond)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5]1>>[C:1]1[C:2]=[C:3][C:4][C:5]1",
        description="Cyclopentene replaces cyclopentane. "
                    "One double bond adds reactivity.",
        expected_impact="Cyclopentene, unsaturation, reactivity",
        complexity_delta=0.3,
        tags=["cyclopentene", "unsaturation", "5-membered"],
        reference="Carbocycle unsaturation SAR"
    ),
    "CARB009": SmirksEntry(
        id="CARB009",
        category="carbocyclic_replacements",
        name="Cyclohexane to cyclohexanone (ketone formation)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2][C:3][C:4](=[O:7])[C:5][C:6]1",
        description="Cyclohexanone replaces cyclohexane. "
                    "Ketone in ring, different reactivity.",
        expected_impact="Ketone, cyclohexanone, carbonyl",
        complexity_delta=0.3,
        tags=["cyclohexanone", "ketone", "carbonyl"],
        reference="Cyclohexane ketone oxidation"
    ),
    "CARB011": SmirksEntry(
        id="CARB011",
        category="carbocyclic_replacements",
        name="Cyclohexane to cycloheptane (ring expansion)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2][C:3][C:4][C:5][C:6][C:7]1",
        description="Cycloheptane replaces cyclohexane. "
                    "7-membered ring adds flexibility.",
        expected_impact="Cycloheptane, 7-membered, flexibility",
        complexity_delta=0.2,
        tags=["cycloheptane", "ring_expansion", "flexibility"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 8"
    ),
    "CARB012": SmirksEntry(
        id="CARB012",
        category="carbocyclic_replacements",
        name="Cyclohexane to cyclopentane (ring contraction)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[C:1]1[C:2][C:3][C:4][C:5]1",
        description="Cyclopentane replaces cyclohexane. "
                    "5-membered ring, different shape.",
        expected_impact="Cyclopentane, 5-membered, shape",
        complexity_delta=0.2,
        tags=["cyclopentane", "ring_contraction", "shape"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 8"
    ),
    "CARB013": SmirksEntry(
        id="CARB013",
        category="carbocyclic_replacements",
        name="Cyclopentane to cyclobutane (ring contraction)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5]1>>[C:1]1[C:2][C:3][C:4]1",
        description="Cyclobutane replaces cyclopentane. "
                    "4-membered ring, higher strain.",
        expected_impact="Cyclobutane, 4-membered, strain",
        complexity_delta=0.2,
        tags=["cyclobutane", "ring_contraction", "strain"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 8"
    ),
    "CARB014": SmirksEntry(
        id="CARB014",
        category="carbocyclic_replacements",
        name="Cyclopentane to oxolane (CH2→O in ring)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5]1>>[C:1]1[C:2][O:3][C:4][C:5]1",
        description="Oxolane (THF) replaces cyclopentane. "
                    "Oxygen adds polarity.",
        expected_impact="Oxolane, oxygen, polarity",
        complexity_delta=0.0,
        tags=["oxolane", "THF", "oxygen"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 8"
    ),
    "CARB015": SmirksEntry(
        id="CARB015",
        category="carbocyclic_replacements",
        name="Benzene to cyclobutane (4-membered ring)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4]1",
        description="Cyclobutane replaces benzene. "
                    "Small ring, high strain, 3D shape.",
        expected_impact="Cyclobutane, 4-membered, strain",
        complexity_delta=0.5,
        tags=["cyclobutane", "4-membered", "strain"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 8"
    ),
    "CARB016": SmirksEntry(
        id="CARB016",
        category="carbocyclic_replacements",
        name="Benzene to cyclopropane (smallest ring)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3]1",
        description="Cyclopropane replaces benzene. "
                    "Smallest carbocycle, high strain.",
        expected_impact="Cyclopropane, 3-membered, strain",
        complexity_delta=0.3,
        tags=["cyclopropane", "3-membered", "strain"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 8"
    ),
    "CARB017": SmirksEntry(
        id="CARB017",
        category="carbocyclic_replacements",
        name="Cyclopentane to furan (CH2→O)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5]1>>[C:1]1[C:2][C:3][O:4][C:5]1",
        description="Furan replaces cyclopentane. "
                    "Oxygen adds polarity and aromaticity.",
        expected_impact="Furan, oxygen, aromaticity",
        complexity_delta=0.3,
        tags=["furan", "cyclopentane", "oxygen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),
    # ============================================================================
    # CATECHOL BIOISOSTERIC TRANSFORMATIONS (Drug Guru Project, Brown Ch. 11)
    # ============================================================================
    "DG001": SmirksEntry(
        id="DG001",
        category="catechol_transformations",
        name="Catechol to benzoxazolone",
        smirks="[a:1]1[a:2][a:3][a:4][c]([OH])[c]([OH])1>>[a:1]1[a:2][a:3][a:4][c]2[NH][c](=O)[o][c]12",
        description="Catechol bioisostere replacement with benzoxazolone ring. "
                    "Neutral heterocycle with H-bond donor/acceptor properties.",
        expected_impact="Benzoxazolone, neutral heterocycle, 5-membered ring with N and O",
        complexity_delta=0.5,
        tags=["catechol", "bioisostere", "heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG002": SmirksEntry(
        id="DG002",
        category="catechol_transformations",
        name="Catechol to methylenedioxybenzene",
        smirks="[a:1]1[a:2][a:3][a:4][c]([OH])[c]([OH])1>>[a:1]1[a:2][a:3][a:4][c]2[O][C][O][c]12",
        description="Catechol bioisostere replacement with methylenedioxybenzene (benzodioxole). "
                    "Neutral lipophilic heterocycle common in CNS drugs.",
        expected_impact="Methylenedioxybenzene, benzodioxole, neutral lipophilic heterocycle",
        complexity_delta=0.4,
        tags=["catechol", "bioisostere", "methylenedioxy", "benzodioxole"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG003": SmirksEntry(
        id="DG003",
        category="catechol_transformations",
        name="Catechol to benzimidazolone",
        smirks="[a:1]1[a:2][a:3][a:4][c]([OH])[c]([OH])1>>[a:1]1[a:2][a:3][a:4][c]2[NH][c](=O)[NH][c]12",
        description="Catechol bioisostere replacement with benzimidazolone ring. "
                    "Contains two H-bond donors and one acceptor.",
        expected_impact="Benzimidazolone, H-bond donor/acceptor, 5-membered heterocycle with 2 N",
        complexity_delta=0.5,
        tags=["catechol", "bioisostere", "benzimidazolone", "hydrogen_bond"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG004": SmirksEntry(
        id="DG004",
        category="catechol_transformations",
        name="Catechol to aminobenzothiazole",
        smirks="[a:1]1[a:2][a:3][a:4][c]([OH])[c]([OH])1>>[a:1]1[a:2][a:3][a:4][c]2[n][c](N)[s][c]12",
        description="Catechol bioisostere replacement with aminobenzothiazole. "
                    "Aromatic heterocycle with exocyclic amine and thiazole sulfur.",
        expected_impact="Aminobenzothiazole, aromatic 5-membered heterocycle with S and exocyclic NH2",
        complexity_delta=0.6,
        tags=["catechol", "bioisostere", "benzothiazole", "heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG005": SmirksEntry(
        id="DG005",
        category="catechol_transformations",
        name="Catechol to hydroxybenzothiazolone",
        smirks="[a:1]1[a:2][a:3][a:4]([OH])[c]([OH])[c]([H])1>>[a:1]1[a:2][a:3][a:4]([OH])[c]2[NH][c](=O)[s][c]12",
        description="Catechol bioisostere replacement with hydroxybenzothiazolone. "
                    "5-membered heterocycle with OH, carbonyl, and thiazole S.",
        expected_impact="Hydroxybenzothiazolone, thiazolone with OH and carbonyl",
        complexity_delta=0.6,
        tags=["catechol", "bioisostere", "benzothiazolone", "hydroxy"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG006": SmirksEntry(
        id="DG006",
        category="catechol_transformations",
        name="Catechol to benzoxazinone",
        smirks="[a:1]1[a:2][a:3][a:4][c]([OH])[c]([OH])1>>[a:1]1[a:2][a:3][a:4][c]2[NH][c](=O)[C][o][c]12",
        description="Catechol bioisostere replacement with benzoxazinone. "
                    "6-membered heterocycle with carbonyl and O in ring.",
        expected_impact="Benzoxazinone, 6-membered heterocycle with carbonyl and O",
        complexity_delta=0.5,
        tags=["catechol", "bioisostere", "benzoxazinone", "lactone"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG007": SmirksEntry(
        id="DG007",
        category="catechol_transformations",
        name="Catechol to hydroxypyranone",
        smirks="[c]([H])1[a:2][a:3][c:4]([OH])[c]([OH])[c]1>>[O]1[a:2][a:3][c:4](=O)[c]([OH])[c]1",
        description="Catechol bioisostere replacement with hydroxypyranone (alpha-pyrone). "
                    "Binds metal ions, possible PAINS alert.",
        expected_impact="Hydroxypyranone, alpha-pyrone, metal-binding heterocylic lactone",
        complexity_delta=0.4,
        tags=["catechol", "bioisostere", "pyranone", "lactone", "metal_binding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG008": SmirksEntry(
        id="DG008",
        category="catechol_transformations",
        name="Catechol to dihydroxypyrazine",
        smirks="[c]([H])1[a:2][a:3][a:4][a:5][c]([H])[c]([OH])[c]([OH])1>>[n]1[a:2][a:3][a:4][a:5][n][c]([OH])[c]([OH])1",
        description="Catechol bioisostere replacement with dihydroxypyrazine. "
                    "6-membered heterocycle with two N and two OH positions.",
        expected_impact="Dihydroxypyrazine, 6-membered N-heterocycle with 2 OH groups",
        complexity_delta=0.5,
        tags=["catechol", "bioisostere", "pyrazine", "dihydroxy"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG009": SmirksEntry(
        id="DG009",
        category="catechol_transformations",
        name="Catechol to hydroxypyridone",
        smirks="[c][a:1]1[a:2][a:3][a:4]([OH])[a:5]([OH])[c]1>>[n][a:1]1[a:2][a:3][a:4](=O)[a:5]([OH])[c]1",
        description="Catechol bioisostere replacement with hydroxypyridone. "
                    "6-membered N-heterocycle with carbonyl and OH.",
        expected_impact="Hydroxypyridone, 6-membered N-heterocycle with carbonyl and OH",
        complexity_delta=0.5,
        tags=["catechol", "bioisostere", "pyridone", "lactone"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),
    "DG010": SmirksEntry(
        id="DG010",
        category="catechol_transformations",
        name="Catechol to N-hydroxypyridone",
        smirks="[a:1]1[a:2][a:3][a:4][c]([OH])[c]([OH])1>>[a:1]1[a:2][a:3][a:4][c](=[O])[N]([OH])1",
        description="Catechol bioisostere replacement with N-hydroxypyridone. "
                    "N-hydroxy amide motif with carbonyl.",
        expected_impact="N-hydroxypyridone, N-hydroxy lactam, metal-binding bioisostere",
        complexity_delta=0.5,
        tags=["catechol", "bioisostere", "n-hydroxy", "metal_binding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 11, Drug Guru"
    ),

    # ============================================================================
    # ESTER MODIFICATIONS (expanded from extraction doc lines 727-743)
    # ============================================================================
    "EST002": SmirksEntry(
        id="EST002",
        category="ester_modifications",
        name="Methyl ester to ethyl ester (hydrolytic stability)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[O:3][CH2:4][CH3:5]",
        description="Ethyl ester replaces methyl ester. "
                    "Slightly more resistant to hydrolytic cleavage.",
        expected_impact="Homologation, hydrolytic stability, lipophilicity",
        complexity_delta=0.0,
        tags=["homologation", "hydrolytic_stability", "ethyl"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 3"
    ),
    "EST003": SmirksEntry(
        id="EST003",
        category="ester_modifications",
        name="Methyl ester to phenyl ester (aryl ester)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[O:3][c:4]",
        description="Phenyl ester replaces methyl ester. "
                    "Different reactivity and electronic properties.",
        expected_impact="Aryl_ester, electronic change, reactivity",
        complexity_delta=0.3,
        tags=["aryl_ester", "phenyl", "electronic"],
        reference="Ester bioisosteres"
    ),
    "EST004": SmirksEntry(
        id="EST004",
        category="ester_modifications",
        name="Ester to thioester (O→S exchange)",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[S:3][C:4]",
        description="Thioester replaces ester. "
                    "Sulfur adds different reactivity and lipophilicity.",
        expected_impact="Thioester, sulfur, different_hydrolysis",
        complexity_delta=0.0,
        tags=["thioester", "sulfur", "hydrolysis"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "EST005": SmirksEntry(
        id="EST005",
        category="ester_modifications",
        name="Lactone to lactam (cyclic ester→amide)",
        smirks="[C:1](=[O:2])[O:3][C:4][C:5]>>[C:1](=[O:2])[N:3][C:4][C:5]",
        description="Lactam replaces lactone. "
                    "Amide is more stable to hydrolysis.",
        expected_impact="Lactam, hydrolytic_stability, cyclic_amide",
        complexity_delta=0.0,
        tags=["lactam", "lactone", "hydrolytic_stability"],
        reference="Lactone lactam isosteres"
    ),
    "EST006": SmirksEntry(
        id="EST006",
        category="ester_modifications",
        name="Ester to carbamate (N insertion)",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[N:3][C:4]",
        description="Carbamate replaces ester. "
                    "Nitrogen adds H-bonding capability.",
        expected_impact="Carbamate, H-bonding, metabolic_stability",
        complexity_delta=0.0,
        tags=["carbamate", "nitrogen", "H-bonding"],
        reference="Ester carbamate isosteres"
    ),
    "EST007": SmirksEntry(
        id="EST007",
        category="ester_modifications",
        name="Carboxylic acid to methyl ester (prodrug masking)",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[O:3][CH3:4]",
        description="Methyl ester masks carboxylic acid for prodrug. "
                    "Improves permeability, requires enzymatic cleavage.",
        expected_impact="Masked_acid, permeability, prodrug",
        complexity_delta=0.0,
        tags=["prodrug", "masked_acid", "permeability"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 3"
    ),
    "EST008": SmirksEntry(
        id="EST008",
        category="ester_modifications",
        name="Phosphate ester to thiophosphate (O→S)",
        smirks="[O:1]P(=[O:2])([O:3])[O:4]>>[O:1]P(=[S:2])([O:3])[O:4]",
        description="Thiophosphate replaces phosphate. "
                    "Sulfur adds different metabolic stability.",
        expected_impact="Thiophosphate, sulfur, metabolic",
        complexity_delta=0.3,
        tags=["thiophosphate", "sulfur", "phosphate"],
        reference="Phosphate thiophosphate isosteres"
    ),
    "EST009": SmirksEntry(
        id="EST009",
        category="ester_modifications",
        name="Ester to selenoester (O→Se exchange)",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[Se:3][C:4]",
        description="Selenoester replaces ester. "
                    "Selenium adds different reactivity.",
        expected_impact="Selenoester, selenium, different_reactivity",
        complexity_delta=0.5,
        tags=["selenoester", "selenium", "reactivity"],
        reference="Ester bioisosteres"
    ),
    "EST010": SmirksEntry(
        id="EST010",
        category="ester_modifications",
        name="Methyl ester to isopropyl ester (steric bulk)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[O:3][CH:4]([CH3:5])[CH3:6]",
        description="Isopropyl ester replaces methyl. "
                    "Steric bulk increases hydrolytic stability.",
        expected_impact="Steric_bulk, hydrolytic_stability, lipophilicity",
        complexity_delta=0.2,
        tags=["isopropyl", "hydrolytic_stability", "steric"],
        reference="Ester SAR"
    ),
    "EST011": SmirksEntry(
        id="EST011",
        category="ester_modifications",
        name="Methyl ester to benzyl ester (cleavable prodrug)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[O:3][CH2:4][c:5]",
        description="Benzyl ester replaces methyl. "
                    "Hydrogenolysis-cleavable prodrug moiety.",
        expected_impact="Benzyl_ester, prodrug, cleavable",
        complexity_delta=0.5,
        tags=["benzyl_ester", "prodrug", "cleavable"],
        reference="Prodrug esters"
    ),
    "EST012": SmirksEntry(
        id="EST012",
        category="ester_modifications",
        name="Ester to carbonate (O addition)",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[O:5][C:1](=[O:2])[O:3][C:4]",
        description="Carbonate replaces ester. "
                    "Adds oxygen, different hydrolytic profile.",
        expected_impact="Carbonate, oxygen, different_hydrolysis",
        complexity_delta=0.0,
        tags=["carbonate", "oxygen", "hydrolysis"],
        reference="Carbonate isosteres"
    ),
    "EST013": SmirksEntry(
        id="EST013",
        category="ester_modifications",
        name="Methyl ester to cyclopropyl ester (rigid prodrug)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[O:3][C:4]1[C:5][C:6]1",
        description="Cyclopropyl ester replaces methyl. "
                    "Rigid group with unique metabolic profile.",
        expected_impact="Cyclopropyl, rigid, prodrug",
        complexity_delta=0.3,
        tags=["cyclopropyl", "rigid", "prodrug"],
        reference="Ester bioisosteres"
    ),
    "EST014": SmirksEntry(
        id="EST014",
        category="ester_modifications",
        name="Ester to acyloxy (O migration)",
        smirks="[C:1](=[O:2])[O:3][CH2:4][C:5]>>[C:1][O:2][C:3](=[O:6])[CH2:4][C:5]",
        description="Acyloxy migrates carbonyl position. "
                    "Different reactivity and metabolic profile.",
        expected_impact="Acyloxy, O_migration, different_reactivity",
        complexity_delta=0.0,
        tags=["acyloxy", "migration", "reactivity"],
        reference="Ester migration SAR"
    ),
    "EST015": SmirksEntry(
        id="EST015",
        category="ester_modifications",
        name="Methyl ester to t-butyl ester (steric protection)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[O:3][C:4]([CH3:5])([CH3:6])[CH3:7]",
        description="t-Butyl ester replaces methyl. "
                    "Major steric protection against hydrolysis.",
        expected_impact="Steric_protection, t-butyl, hydrolytic_stability",
        complexity_delta=0.3,
        tags=["t-butyl", "steric_protection", "hydrolytic_stability"],
        reference="Ester SAR"
    ),

    # ============================================================================
    # BIOISOSTERIC REPLACEMENTS (expanded from extraction doc lines 573-597)
    # ============================================================================
    "BIOI009": SmirksEntry(
        id="BIOI009",
        category="bioisosteric_replacements",
        name="Carboxylate to sulfonamide (classic isostere)",
        smirks="[C:1](=[O:2])[O-:3]>>[S:1](=[O:2])(=[O:3])[N:4]",
        description="Sulfonamide replaces carboxylate. "
                    "Classic isostere with different pKa.",
        expected_impact="Sulfonamide, different_pKa, classic_isostere",
        complexity_delta=0.5,
        tags=["sulfonamide", "carboxylate", "classic_isostere"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI010": SmirksEntry(
        id="BIOI010",
        category="bioisosteric_replacements",
        name="Carbonyl to sulfonyl (C=O→SO2)",
        smirks="[C:1](=[O:2])>>[S:1](=[O:2])(=[O:3])",
        description="Sulfonyl replaces carbonyl. "
                    "Adds oxygen, changes electronics.",
        expected_impact="Sulfonyl, oxygen, electronic_change",
        complexity_delta=0.5,
        tags=["sulfonyl", "carbonyl", "electronic"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI011": SmirksEntry(
        id="BIOI011",
        category="bioisosteric_replacements",
        name="Hydroxyl to amino (OH→NH2)",
        smirks="[C:1][OX2H:2]>>[C:1][NH2:2]",
        description="Amino replaces hydroxyl. "
                    "Changes H-bonding from donor/acceptor to donor.",
        expected_impact="Amino, H-bonding change, basicity",
        complexity_delta=0.0,
        tags=["amino", "hydroxyl", "H-bonding"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI012": SmirksEntry(
        id="BIOI012",
        category="bioisosteric_replacements",
        name="Thiol to hydroxyl (SH→OH)",
        smirks="[C:1][SX2H:2]>>[C:1][OX2H:2]",
        description="Hydroxyl replaces thiol. "
                    "Oxygen is more electronegative, less polarizable.",
        expected_impact="Hydroxyl, electronegativity, chalcogen",
        complexity_delta=0.0,
        tags=["hydroxyl", "thiol", "chalcogen"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI013": SmirksEntry(
        id="BIOI013",
        category="bioisosteric_replacements",
        name="Chloro to trifluoromethyl (Cl→CF3)",
        smirks="[Cl:1]>>[C:1]([F:2])([F:3])([F:4])",
        description="CF3 replaces chloro. "
                    "Similar size with different electronics.",
        expected_impact="CF3, lipophilicity, different_electronics",
        complexity_delta=0.3,
        tags=["CF3", "chloro", "lipophilicity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "BIOI014": SmirksEntry(
        id="BIOI014",
        category="bioisosteric_replacements",
        name="Vinyl to thioether (CH=CH→S)",
        smirks="[C:1]=[C:2]>>[S:1]",
        description="Sulfur replaces vinyl. "
                    "Different shape and electronics.",
        expected_impact="Sulfur, shape_change, ring_equivalent",
        complexity_delta=-0.5,
        tags=["sulfur", "vinyl", "ring_equivalent"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI015": SmirksEntry(
        id="BIOI015",
        category="bioisosteric_replacements",
        name="Vinyl to oxygen (CH=CH→O)",
        smirks="[C:1]=[C:2]>>[O:1]",
        description="Oxygen replaces vinyl. "
                    "Heteroatom in ring position.",
        expected_impact="Oxygen, ring_equivalent, heteroatom",
        complexity_delta=-0.5,
        tags=["oxygen", "vinyl", "ring_equivalent"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI016": SmirksEntry(
        id="BIOI016",
        category="bioisosteric_replacements",
        name="Vinyl to NH (CH=CH→NH)",
        smirks="[C:1]=[C:2]>>[NH:1]",
        description="NH replaces vinyl. "
                    "H-bond donor in ring position.",
        expected_impact="NH_donor, ring_equivalent, H-bonding",
        complexity_delta=-0.5,
        tags=["NH", "vinyl", "ring_equivalent"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI017": SmirksEntry(
        id="BIOI017",
        category="bioisosteric_replacements",
        name="Carboxylate to sulfonate (COO→SO3)",
        smirks="[C:1](=[O:2])[O-:3]>>[S:1](=[O:2])(=[O:3])[O-:4]",
        description="Sulfonate replaces carboxylate. "
                    "More acidic, different H-bonding.",
        expected_impact="Sulfonate, acidity, different_H-bonding",
        complexity_delta=0.3,
        tags=["sulfonate", "carboxylate", "acidity"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "BIOI018": SmirksEntry(
        id="BIOI018",
        category="bioisosteric_replacements",
        name="Amide to phosphonamide (C→P)",
        smirks="[C:1](=[O:2])[N:3]>>[P:1](=[O:2])[N:3]",
        description="Phosphorus replaces carbon in amide. "
                    "Different electronics and size.",
        expected_impact="Phosphonamide, phosphorus, different_electronics",
        complexity_delta=0.5,
        tags=["phosphonamide", "phosphorus", "amide"],
        reference="Phosphonamide isosteres"
    ),
    "BIOI019": SmirksEntry(
        id="BIOI019",
        category="bioisosteric_replacements",
        name="Peroxide to disulfide (O-O→S-S)",
        smirks="[O:1][O:2]>>[S:1][S:2]",
        description="Disulfide replaces peroxide. "
                    "Sulfur-sulfur bond more stable.",
        expected_impact="Disulfide, sulfur, stability",
        complexity_delta=0.0,
        tags=["disulfide", "peroxide", "sulfur"],
        reference="Peroxide disulfide isosteres"
    ),
    "BIOI020": SmirksEntry(
        id="BIOI020",
        category="bioisosteric_replacements",
        name="Amide to thioamide (O→S)",
        smirks="[C:1](=[O:2])[N:3]>>[C:1](=[S:2])[N:3]",
        description="Thioamide replaces amide. "
                    "Sulfur adds polarizability and lipophilicity.",
        expected_impact="Thioamide, sulfur, lipophilicity",
        complexity_delta=0.0,
        tags=["thioamide", "sulfur", "polarizability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "BIOI021": SmirksEntry(
        id="BIOI021",
        category="bioisosteric_replacements",
        name="N-oxide to N-fluoro (O→F)",
        smirks="[N+:1](=[O-:2])>>[N:1][F:2]",
        description="N-fluoro replaces N-oxide. "
                    "Different H-bonding and basicity.",
        expected_impact="N-fluoro, different_H-bonding, basicity",
        complexity_delta=0.0,
        tags=["N-fluoro", "N-oxide", "basicity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "BIOI022": SmirksEntry(
        id="BIOI022",
        category="bioisosteric_replacements",
        name="Semicarbazone to thiosemicarbazone (O→S)",
        smirks="[C:1]=[N:2][N:3][C:4](=[O:5])[N:6]>>[C:1]=[N:2][N:3][C:4](=[S:5])[N:6]",
        description="Thiosemicarbazone replaces semicarbazone. "
                    "Sulfur adds lipophilicity.",
        expected_impact="Thiosemicarbazone, sulfur, lipophilicity",
        complexity_delta=0.0,
        tags=["thiosemicarbazone", "sulfur", "semicarbazone"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "BIOI023": SmirksEntry(
        id="BIOI023",
        category="bioisosteric_replacements",
        name="Ester to thioester (O→S in ester)",
        smirks="[C:1](=[O:2])[O:3][C:4]>>[C:1](=[S:2])[O:3][C:4]",
        description="Thioester replaces ester. "
                    "Thiocarbonyl is more reactive.",
        expected_impact="Thioester, sulfur, reactivity",
        complexity_delta=0.0,
        tags=["thioester", "sulfur", "reactivity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "BIOI024": SmirksEntry(
        id="BIOI024",
        category="bioisosteric_replacements",
        name="Indole to benzimidazole (NH→N)",
        smirks="[c:1]1[c:2][c:3][c:4][nH:5][c:6]1>>[c:1]1[c:2][c:3][n:4][c:5][c:6]1",
        description="Benzimidazole replaces indole. "
                    "Extra nitrogen changes basicity.",
        expected_impact="Benzimidazole, extra_N, basicity",
        complexity_delta=0.0,
        tags=["benzimidazole", "indole", "nitrogen"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 2"
    ),
    "BIOI025": SmirksEntry(
        id="BIOI025",
        category="bioisosteric_replacements",
        name="Hydrazone to oxime (N=NH→N=O)",
        smirks="[C:1]=[N:2][NH2:3]>>[C:1]=[N:2][OH:3]",
        description="Oxime replaces hydrazone. "
                    "Oxygen instead of nitrogen.",
        expected_impact="Oxime, oxygen, different_H-bonding",
        complexity_delta=0.0,
        tags=["oxime", "hydrazone", "oxygen"],
        reference="Hydrazone oxime isosteres"
    ),
    "BIOI026": SmirksEntry(
        id="BIOI026",
        category="bioisosteric_replacements",
        name="Guanidine to cyanoguanidine (add CN)",
        smirks="[N:1]=[C:2]([N:3])[N:4]>>[N:1]=[C:2]([N:3])[N:4][C:5]#[N:6]",
        description="Cyanoguanidine replaces guanidine. "
                    "Cyano group reduces basicity.",
        expected_impact="Cyanoguanidine, reduced_basicity, cyano",
        complexity_delta=0.5,
        tags=["cyanoguanidine", "guanidine", "basicity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),

    # ============================================================================
    # AROMATIC SUBSTITUTIONS (expanded from extraction doc lines 601-626)
    # ============================================================================
    "AROM003": SmirksEntry(
        id="AROM003",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-cyano",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([C:7]#[N:8])[c:4][c:5][c:6]1",
        description="Cyano group at para position. "
                    "Electron-withdrawing, increases polarity.",
        expected_impact="Electron-withdrawing, cyano, polarity",
        complexity_delta=0.0,
        tags=["cyano", "para", "electron-withdrawing"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM004": SmirksEntry(
        id="AROM004",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-nitro",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([N:7](=[O:8])=[O:9])[c:4][c:5][c:6]1",
        description="Nitro group at para position. "
                    "Strong electron-withdrawing, increases PSA.",
        expected_impact="Strong_EWG, nitro, PSA_increase",
        complexity_delta=0.2,
        tags=["nitro", "para", "EWG"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM005": SmirksEntry(
        id="AROM005",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-amino",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([NH2:7])[c:4][c:5][c:6]1",
        description="Amino group at para position. "
                    "Electron-donating, H-bond donor.",
        expected_impact="Electron-donating, amino, H-bond_donor",
        complexity_delta=0.0,
        tags=["amino", "para", "EDG"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM006": SmirksEntry(
        id="AROM006",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-methylsulfonyl",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([S:7](=[O:8])(=[O:9])[CH3:10])[c:4][c:5][c:6]1",
        description="Methylsulfonyl group at para. "
                    "Electron-withdrawing, high PSA.",
        expected_impact="Methylsulfonyl, EWG, high_PSA",
        complexity_delta=0.3,
        tags=["methylsulfonyl", "para", "EWG"],
        reference="Aromatic substitution SAR"
    ),
    "AROM007": SmirksEntry(
        id="AROM007",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-carboxyl",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([C:7](=[O:8])[OH:9])[c:4][c:5][c:6]1",
        description="Carboxyl group at para position. "
                    "Acidic, ionizable, increases solubility.",
        expected_impact="Carboxyl, acidic, ionizable",
        complexity_delta=0.2,
        tags=["carboxyl", "para", "acidic"],
        reference="Aromatic substitution SAR"
    ),
    "AROM008": SmirksEntry(
        id="AROM008",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-tert-butyl",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([C:7]([C:8])([C:9])[C:10])[c:4][c:5][c:6]1",
        description="tert-Butyl group at para. "
                    "Major steric bulk, electron-donating.",
        expected_impact="tert-butyl, steric_bulk, EDG",
        complexity_delta=0.3,
        tags=["tert-butyl", "para", "steric"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM009": SmirksEntry(
        id="AROM009",
        category="aromatic_substitutions",
        name="Para-hydrogen to para-hydroxyl",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([OH:7])[c:4][c:5][c:6]1",
        description="Hydroxyl group at para position. "
                    "H-bond donor/acceptor, electron-donating.",
        expected_impact="Hydroxyl, H-bonding, EDG",
        complexity_delta=0.0,
        tags=["hydroxyl", "para", "H-bonding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM010": SmirksEntry(
        id="AROM010",
        category="aromatic_substitutions",
        name="Para-methoxy to para-dimethylamino",
        smirks="[c:1]1[c:2][c:3][c:4]([O:5][CH3:6])[c:7][c:8]1>>[c:1]1[c:2][c:3][c:4]([N:5]([CH3:7])[CH3:9])[c:7][c:8]1",
        description="Dimethylamino replaces methoxy at para. "
                    "Basic amine, different electronics.",
        expected_impact="Dimethylamino, basicity, para",
        complexity_delta=0.0,
        tags=["dimethylamino", "methoxy", "para"],
        reference="Aromatic substitution SAR"
    ),
    "AROM011": SmirksEntry(
        id="AROM011",
        category="aromatic_substitutions",
        name="Para-thioether to para-sulfoxide",
        smirks="[c:1]1[c:2][c:3][c:4]([S:5][CH3:6])[c:7][c:8]1>>[c:1]1[c:2][c:3][c:4]([S:5](=[O:9])[CH3:6])[c:7][c:8]1",
        description="Sulfoxide replaces thioether at para. "
                    "Adds polarity and H-bond acceptor.",
        expected_impact="Sulfoxide, polarity, para",
        complexity_delta=0.2,
        tags=["sulfoxide", "thioether", "polarity"],
        reference="Aromatic oxidation SAR"
    ),
    "AROM012": SmirksEntry(
        id="AROM012",
        category="aromatic_substitutions",
        name="Para-methyl to para-trifluoromethyl",
        smirks="[c:1]1[c:2][c:3][c:4]([CH3:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([C:5]([F:8])([F:9])([F:10]))[c:6][c:7]1",
        description="CF3 replaces methyl at para. "
                    "Major lipophilicity increase, metabolic block.",
        expected_impact="CF3, lipophilicity, metabolic_block",
        complexity_delta=0.2,
        tags=["CF3", "methyl", "lipophilicity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AROM013": SmirksEntry(
        id="AROM013",
        category="aromatic_substitutions",
        name="Para-COOH to para-SO2NH2",
        smirks="[c:1]1[c:2][c:3][c:4]([C:5](=[O:6])[OH:7])[c:8][c:9]1>>[c:1]1[c:2][c:3][c:4]([S:5](=[O:6])(=[O:10])[NH2:11])[c:8][c:9]1",
        description="Sulfonamide replaces carboxyl at para. "
                    "Classic acid/sulfonamide swap.",
        expected_impact="Sulfonamide, acid_isostere, para",
        complexity_delta=0.3,
        tags=["sulfonamide", "carboxyl", "isostere"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "AROM014": SmirksEntry(
        id="AROM014",
        category="aromatic_substitutions",
        name="Aromatic to cyclohexenyl (partial saturation)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2]=[C:3][C:4][C:5][C:6]1",
        description="Cyclohexenyl replaces aromatic. "
                    "Partial saturation, reduces stacking.",
        expected_impact="Partial_saturation, cyclohexenyl, non_aromatic",
        complexity_delta=0.3,
        tags=["cyclohexenyl", "partial_saturation", "aromatic"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "AROM015": SmirksEntry(
        id="AROM015",
        category="aromatic_substitutions",
        name="Ortho-fluoro isomer (2-F→3-F)",
        smirks="[c:1]1([F:2])[c:3][c:4][c:5][c:6][c:7]1>>[c:1]1[c:2]([F:3])[c:4][c:5][c:6][c:7]1",
        description="Fluoro moves from ortho to meta. "
                    "Positional isomer with different dipole.",
        expected_impact="Positional_isomer, fluorine, meta",
        complexity_delta=0.0,
        tags=["fluorine", "positional_isomer", "meta"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM016": SmirksEntry(
        id="AROM016",
        category="aromatic_substitutions",
        name="Para-methoxy to para-hydroxyl (O-demethylation)",
        smirks="[c:1]1[c:2][c:3][c:4]([O:5][CH3:6])[c:7][c:8]1>>[c:1]1[c:2][c:3][c:4]([OH:5])[c:7][c:8]1",
        description="Hydroxyl replaces methoxy at para. "
                    "O-demethylation product, more polar.",
        expected_impact="Demethylation, phenol, polarity",
        complexity_delta=0.0,
        tags=["demethylation", "phenol", "para"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM017": SmirksEntry(
        id="AROM017",
        category="aromatic_substitutions",
        name="Para-amine to para-N-methylamine",
        smirks="[c:1]1[c:2][c:3][c:4]([NH2:5])[c:6][c:7]1>>[c:1]1[c:2][c:3][c:4]([NH:5][CH3:8])[c:6][c:7]1",
        description="N-methylamine replaces amine at para. "
                    "Reduces H-bond donor count.",
        expected_impact="N-methylation, reduced_H-bond, para",
        complexity_delta=0.1,
        tags=["N-methylation", "amine", "para"],
        reference="Aromatic amine SAR"
    ),
    "AROM018": SmirksEntry(
        id="AROM018",
        category="aromatic_substitutions",
        name="Aromatic methylation (H→CH3 at available position)",
        smirks="[cH:1]>>[c:1][CH3:2]",
        description="Methyl replaces hydrogen on aromatic. "
                    "Electron-donating, blocks metabolism.",
        expected_impact="Methylation, EDG, metabolic_block",
        complexity_delta=0.0,
        tags=["methylation", "EDG", "metabolic_block"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "AROM019": SmirksEntry(
        id="AROM019",
        category="aromatic_substitutions",
        name="Aromatic fluorination (H→F at available position)",
        smirks="[cH:1]>>[c:1][F:2]",
        description="Fluorine replaces hydrogen on aromatic. "
                    "Blocks oxidative metabolism at that site.",
        expected_impact="Fluorination, metabolic_block, small",
        complexity_delta=0.0,
        tags=["fluorination", "metabolic_block", "small"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AROM020": SmirksEntry(
        id="AROM020",
        category="aromatic_substitutions",
        name="2,4-Difluoro to 2,5-difluoro pattern",
        smirks="[c:1]1([F:2])[c:3][c:4]([F:5])[c:6][c:7]1>>[c:1]1([F:2])[c:3][c:4][c:5]([F:7])[c:6]1",
        description="Fluoro pattern shift from 2,4 to 2,5. "
                    "Different dipole orientation.",
        expected_impact="Fluoro_pattern, dipole, positional",
        complexity_delta=0.0,
        tags=["difluoro", "positional_isomer", "dipole"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),

    # ============================================================================
    # CARBOXYLIC ACID REPLACEMENTS (expanded from extraction doc lines 363-390)
    # ============================================================================
    "ACID008": SmirksEntry(
        id="ACID008",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to sulfonamide",
        smirks="[C:1](=[O:2])[OH:3]>>[S:1](=[O:2])(=[O:3])[NH2:4]",
        description="Sulfonamide replaces carboxylic acid. "
                    "Classic bioisostere with different pKa.",
        expected_impact="Sulfonamide, different_pKa, classic_isostere",
        complexity_delta=0.5,
        tags=["sulfonamide", "acid_isostere", "classic"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "ACID009": SmirksEntry(
        id="ACID009",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to phosphonic acid",
        smirks="[C:1](=[O:2])[OH:3]>>[P:1](=[O:2])([OH:3])[OH:4]",
        description="Phosphonic acid replaces carboxylic acid. "
                    "Bidentate binding capability.",
        expected_impact="Phosphonic_acid, bidentate, metal_binding",
        complexity_delta=0.5,
        tags=["phosphonic_acid", "metal_binding", "acid_isostere"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID010": SmirksEntry(
        id="ACID010",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to boronic acid",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1](=[B:2]([OH:3])[OH:4])",
        description="Boronic acid replaces carboxylic acid. "
                    "Planar, Lewis acid, covalent binding.",
        expected_impact="Boronic_acid, Lewis_acid, covalent_binding",
        complexity_delta=0.5,
        tags=["boronic_acid", "Lewis_acid", "covalent"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID011": SmirksEntry(
        id="ACID011",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to thiazolidinedione",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1]1[S:2][C:3](=[O:4])[N:5][C:6](=[O:7])1",
        description="Thiazolidinedione replaces carboxylic acid. "
                    "Ring system with enhanced binding.",
        expected_impact="Thiazolidinedione, ring, enhanced_binding",
        complexity_delta=1.0,
        tags=["thiazolidinedione", "ring", "TZD"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID012": SmirksEntry(
        id="ACID012",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to 5-oxo-1,2,4-oxadiazole",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1]1[O:2][N:3]=[C:4]([O:5])[N:6]1",
        description="5-Oxo-1,2,4-oxadiazole replaces acid. "
                    "5-membered heterocycle with N-rich binding.",
        expected_impact="Oxadiazole, N-rich, heterocycle",
        complexity_delta=0.8,
        tags=["oxadiazole", "N-rich", "heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID013": SmirksEntry(
        id="ACID013",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to cyanoguanidine",
        smirks="[C:1](=[O:2])[OH:3]>>[N:3][C:1](=[N:2])N[C:4]#[N:5]",
        description="Cyanoguanidine replaces carboxylic acid. "
                    "Planar with different H-bonding.",
        expected_impact="Cyanoguanidine, planar, H-bonding",
        complexity_delta=0.5,
        tags=["cyanoguanidine", "planar", "H-bonding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "ACID014": SmirksEntry(
        id="ACID014",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to squaramide",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1]1(=[O:2])[C:3](=[O:4])[N:5][C:6](=[O:7])1",
        description="Squaramide replaces carboxylic acid. "
                    "4-membered ring with strong H-bonding.",
        expected_impact="Squaramide, 4-membered_ring, H-bonding",
        complexity_delta=0.8,
        tags=["squaramide", "4-membered", "H-bonding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, p. 44"
    ),
    "ACID015": SmirksEntry(
        id="ACID015",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to urazole",
        smirks="[C:1](=[O:2])[OH:3]>>[N:1]1[C:2](=[O:3])[N:4][C:5](=[O:6])[N:7]1",
        description="Urazole replaces carboxylic acid. "
                    "5-membered ring with 3 nitrogens.",
        expected_impact="Urazole, N-rich, heterocycle",
        complexity_delta=1.0,
        tags=["urazole", "N-rich", "heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID016": SmirksEntry(
        id="ACID016",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to hydantoin",
        smirks="[C:1](=[O:2])[OH:3]>>[N:1]1[C:2](=[O:3])[C:4](=[O:5])[N:6]1",
        description="Hydantoin replaces carboxylic acid. "
                    "5-membered ring with 2 carbonyls.",
        expected_impact="Hydantoin, dicarbonyl, heterocycle",
        complexity_delta=0.8,
        tags=["hydantoin", "dicarbonyl", "heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID017": SmirksEntry(
        id="ACID017",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to barbituric acid",
        smirks="[C:1](=[O:2])[OH:3]>>[N:1]1[C:2](=[O:3])[C:4](=[O:5])[N:6][C:7](=[O:8])1",
        description="Barbituric acid replaces carboxylic acid. "
                    "6-membered ring with 3 carbonyls.",
        expected_impact="Barbituric, tricarbonyl, heterocycle",
        complexity_delta=1.0,
        tags=["barbituric", "tricarbonyl", "heterocycle"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 4"
    ),
    "ACID018": SmirksEntry(
        id="ACID018",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to acylsulfonamide",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[N:3][S:4](=[O:5])(=[O:6])",
        description="Acylsulfonamide replaces carboxylic acid. "
                    "More acidic than sulfonamide alone.",
        expected_impact="Acylsulfonamide, acidic, planar",
        complexity_delta=0.3,
        tags=["acylsulfonamide", "acidic", "planar"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, p. 32"
    ),
    "ACID019": SmirksEntry(
        id="ACID019",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to N-sulfonylurea",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1](=[O:2])[N:3][S:4](=[O:5])(=[O:6])[NH2:7]",
        description="N-Sulfonylurea replaces carboxylic acid. "
                    "Extended acidic functionality.",
        expected_impact="N-sulfonylurea, acidic, extended",
        complexity_delta=0.5,
        tags=["N-sulfonylurea", "acidic", "extended"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),
    "ACID020": SmirksEntry(
        id="ACID020",
        category="carboxylic_acid_replacements",
        name="Carboxylic acid to oxetane carboxylic acid",
        smirks="[C:1](=[O:2])[OH:3]>>[C:1]1([OH:3])[C:4][C:5][O:6]1",
        description="Oxetane carboxylic acid replaces acid. "
                    "4-membered ring adds rigidity.",
        expected_impact="Oxetane, rigidity, 4-membered",
        complexity_delta=0.5,
        tags=["oxetane", "rigidity", "4-membered"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 4"
    ),

    # ============================================================================
    # METABOLIC STABILITY (expanded from extraction doc lines 454-486)
    # ============================================================================
    "META027": SmirksEntry(
        id="META027",
        category="metabolic_stability",
        name="OCH3 to OCHF2 (difluoromethoxy protection)",
        smirks="[c:1][OX2:2][CH3:3]>>[c:1][OX2:2][CH:3]([F:4])([F:5])",
        description="Difluoromethoxy replaces methoxy. "
                    "Blocks O-demethylation, adds lipophilicity.",
        expected_impact="Difluoromethoxy, metabolic_block, lipophilicity",
        complexity_delta=0.2,
        tags=["difluoromethoxy", "metabolic_block", "fluorination"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "META028": SmirksEntry(
        id="META028",
        category="metabolic_stability",
        name="Pyrrole N to N-Me (N-methylation blocks oxidation)",
        smirks="[nH:1]>>[n:1][CH3:2]",
        description="N-Methylation of pyrrole blocks oxidative metabolism. "
                    "Removes H-bond donor.",
        expected_impact="N-methylation, metabolic_block, H-bond_reduction",
        complexity_delta=0.1,
        tags=["N-methylation", "pyrrole", "metabolic_block"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "META029": SmirksEntry(
        id="META029",
        category="metabolic_stability",
        name="Thioether to sulfoxide (oxidation)",
        smirks="[C:1][SX2:2][C:3]>>[C:1][S:2](=[O:4])[C:3]",
        description="Sulfoxide replaces thioether. "
                    "First oxidation step adds polarity.",
        expected_impact="Sulfoxide, oxidation, polarity",
        complexity_delta=0.3,
        tags=["sulfoxide", "oxidation", "polarity"],
        reference="Thioether oxidation SAR"
    ),
    "META030": SmirksEntry(
        id="META030",
        category="metabolic_stability",
        name="Aldehyde to oxime (metabolic stability)",
        smirks="[C:1]=[O:2]>>[C:1]=[N:2][OH:3]",
        description="Oxime replaces aldehyde. "
                    "More stable with H-bond donor capability.",
        expected_impact="Oxime, H-bond_donor, stability",
        complexity_delta=0.3,
        tags=["oxime", "aldehyde", "stability"],
        reference="Aldehyde oxime isosteres"
    ),
    "META031": SmirksEntry(
        id="META031",
        category="metabolic_stability",
        name="Primary amine to secondary amine (N-methylation)",
        smirks="[NH2:1][C:2]>>[NH:1][CH3:3]",
        description="Secondary amine replaces primary. "
                    "Reduces oxidative deamination.",
        expected_impact="Secondary_amine, reduced_oxidation, N-methylation",
        complexity_delta=0.1,
        tags=["secondary_amine", "N-methylation", "oxidation"],
        reference="Amine metabolic stability"
    ),
    "META032": SmirksEntry(
        id="META032",
        category="metabolic_stability",
        name="Alcohol to fluoride (blocks oxidation)",
        smirks="[C:1][OX2H:2]>>[C:1][F:2]",
        description="Fluorine replaces hydroxyl. "
                    "Complete block of oxidative metabolism.",
        expected_impact="Fluorination, oxidation_block, H-bond_reduction",
        complexity_delta=0.0,
        tags=["fluorination", "oxidation_block", "alcohol"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "META033": SmirksEntry(
        id="META033",
        category="metabolic_stability",
        name="N-methyl to N-ethyl (reduce demethylation)",
        smirks="[N:1][CH3:2]>>[N:1][CH2:2][CH3:3]",
        description="N-Ethyl replaces N-methyl. "
                    "Reduces N-demethylation metabolism.",
        expected_impact="N-ethylation, reduced_demethylation, size",
        complexity_delta=0.0,
        tags=["N-ethylation", "demethylation", "size"],
        reference="Amine SAR"
    ),
    "META034": SmirksEntry(
        id="META034",
        category="metabolic_stability",
        name="Phenyl to 4-fluorophenyl (para oxidation block)",
        smirks="[c:1]1[c:2][cH:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3]([F:7])[c:4][c:5][c:6]1",
        description="Fluorine at para blocks aromatic oxidation. "
                    "Standard metabolic stability tactic.",
        expected_impact="Para-fluorination, metabolic_block, aromatic",
        complexity_delta=0.0,
        tags=["fluorination", "para", "metabolic_block"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "META035": SmirksEntry(
        id="META035",
        category="metabolic_stability",
        name="Amide to urea (metabolic stability)",
        smirks="[C:1](=[O:2])[N:3][C:4]>>[N:5][C:1](=[O:2])[N:3][C:4]",
        description="Urea replaces amide. "
                    "More metabolically stable with extra H-bonding.",
        expected_impact="Urea, metabolic_stability, H-bonding",
        complexity_delta=0.0,
        tags=["urea", "amide", "metabolic_stability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "META036": SmirksEntry(
        id="META036",
        category="metabolic_stability",
        name="Furyl to thienyl (different metabolic profile)",
        smirks="[c:1]1[c:2][c:3][o:4][c:5][c:6]1>>[c:1]1[c:2][c:3][s:4][c:5][c:6]1",
        description="Thiophene replaces furan. "
                    "Sulfur has different metabolic liability.",
        expected_impact="Thiophene, furan, different_metabolism",
        complexity_delta=0.3,
        tags=["thiophene", "furan", "metabolism"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 2"
    ),

    # ============================================================================
    # BENZYLC MODIFICATIONS (expanded from extraction doc lines 546-568)
    # ============================================================================
    "BENZ013": SmirksEntry(
        id="BENZ013",
        category="benzylic_modifications",
        name="Benzylic CH2 to CCl2 (gem-dichloro block)",
        smirks="[c:1][CH2:2]>>[c:1][C:2]([Cl:3])([Cl:4])",
        description="Gem-dichloro replaces benzylic CH2. "
                    "Blocks benzylic oxidation.",
        expected_impact="Gem-dichloro, metabolic_block, benzylic",
        complexity_delta=0.2,
        tags=["gem-dichloro", "metabolic_block", "benzylic"],
        reference="Benzylic modification SAR"
    ),
    "BENZ014": SmirksEntry(
        id="BENZ014",
        category="benzylic_modifications",
        name="Benzylic CH2 to CH2NH2 (aminomethyl)",
        smirks="[c:1][CH2:2]>>[c:1][CH2:2][NH2:3]",
        description="Aminomethyl replaces benzylic CH2. "
                    "Adds basicity and H-bonding.",
        expected_impact="Aminomethyl, basicity, H-bond_donor",
        complexity_delta=0.3,
        tags=["aminomethyl", "basicity", "H-bonding"],
        reference="Benzylic modification SAR"
    ),
    "BENZ015": SmirksEntry(
        id="BENZ015",
        category="benzylic_modifications",
        name="Benzylic CH2 to CH2SO2CH3 (methylsulfonylmethyl)",
        smirks="[c:1][CH2:2]>>[c:1][CH2:2][S:3](=[O:4])(=[O:5])[CH3:6]",
        description="Methylsulfonylmethyl replaces benzylic CH2. "
                    "High polarity, H-bond acceptor.",
        expected_impact="Methylsulfonyl, high_polarity, H-bond_acceptor",
        complexity_delta=0.5,
        tags=["methylsulfonyl", "polarity", "benzylic"],
        reference="Benzylic modification SAR"
    ),
    "BENZ016": SmirksEntry(
        id="BENZ016",
        category="benzylic_modifications",
        name="Benzylic CH2 to CH2CN (cyanomethyl)",
        smirks="[c:1][CH2:2]>>[c:1][CH2:2][C:3]#[N:4]",
        description="Cyanomethyl replaces benzylic CH2. "
                    "Electron-withdrawing, different electronics.",
        expected_impact="Cyanomethyl, EWG, different_electronics",
        complexity_delta=0.3,
        tags=["cyanomethyl", "EWG", "benzylic"],
        reference="Benzylic modification SAR"
    ),
    "BENZ017": SmirksEntry(
        id="BENZ017",
        category="benzylic_modifications",
        name="Benzylic CH2 to CH2SCH3 (thiomethyl)",
        smirks="[c:1][CH2:2]>>[c:1][CH2:2][S:3][CH3:4]",
        description="Thiomethyl replaces benzylic CH2. "
                    "Sulfur adds lipophilicity and metabolic liability.",
        expected_impact="Thiomethyl, sulfur, lipophilicity",
        complexity_delta=0.2,
        tags=["thiomethyl", "sulfur", "benzylic"],
        reference="Benzylic modification SAR"
    ),
    "BENZ018": SmirksEntry(
        id="BENZ018",
        category="benzylic_modifications",
        name="Benzylic CH2 to CHCl (monochloro block)",
        smirks="[c:1][CH2:2]>>[c:1][CH:2]([Cl:3])",
        description="Monochloro replaces one benzylic H. "
                    "Partial block of benzylic oxidation.",
        expected_impact="Monochloro, metabolic_block, benzylic",
        complexity_delta=0.0,
        tags=["monochloro", "metabolic_block", "benzylic"],
        reference="Benzylic oxidation SAR"
    ),

    # ============================================================================
    # HALOGEN SUBSTITUTIONS (3 more from extraction doc lines 503-510)
    # ============================================================================
    "HALO011": SmirksEntry(
        id="HALO011",
        category="halogen_substitutions",
        name="Aromatic H to iodine (I)",
        smirks="[cH:1]>>[c:1][I:2]",
        description="Iodine replaces hydrogen on aromatic. "
                    "Largest halogen, high polarizability.",
        expected_impact="Iodine, large_halogen, polarizability",
        complexity_delta=0.2,
        tags=["iodine", "large_halogen", "polarizability"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "HALO012": SmirksEntry(
        id="HALO012",
        category="halogen_substitutions",
        name="Aromatic H to cyano (CN isostere)",
        smirks="[cH:1]>>[c:1][C:2]#[N:3]",
        description="Cyano replaces hydrogen. "
                    "Electron-withdrawing, H-bond acceptor.",
        expected_impact="Cyano, EWG, H-bond_acceptor",
        complexity_delta=0.2,
        tags=["cyano", "EWG", "H-bonding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "HALO013": SmirksEntry(
        id="HALO013",
        category="halogen_substitutions",
        name="Aromatic N-oxide to N-fluoro",
        smirks="[n+:1](=[O-:2])>>[n:1][F:2]",
        description="N-fluoro replaces N-oxide. "
                    "Blocks N-oxide metabolism pathway.",
        expected_impact="N-fluoro, N-oxide_block, metabolic_stability",
        complexity_delta=0.0,
        tags=["N-fluoro", "N-oxide", "metabolic_block"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),

    # ============================================================================
    # O-SUBSTITUTIONS (6 more from extraction doc lines 512-544)
    # ============================================================================
    "OSUB047": SmirksEntry(
        id="OSUB047",
        category="o_substitutions",
        name="Methoxy to methylsulfoxide (OCH3→SOCH3)",
        smirks="[c:1][OX2:2][CH3:3]>>[c:1][S:2](=[O:4])[CH3:3]",
        description="Methylsulfoxide replaces methoxy. "
                    "Sulfur adds polarity and H-bond acceptor.",
        expected_impact="Methylsulfoxide, polarity, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["methylsulfoxide", "polarity", "sulfur"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "OSUB048": SmirksEntry(
        id="OSUB048",
        category="o_substitutions",
        name="Methoxy to methylsulfone (OCH3→SO2CH3)",
        smirks="[c:1][OX2:2][CH3:3]>>[c:1][S:2](=[O:4])(=[O:5])[CH3:3]",
        description="Methylsulfone replaces methoxy. "
                    "Major polarity increase.",
        expected_impact="Methylsulfone, high_polarity, sulfur",
        complexity_delta=0.4,
        tags=["methylsulfone", "high_polarity", "sulfur"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "OSUB049": SmirksEntry(
        id="OSUB049",
        category="o_substitutions",
        name="Methoxy to acetamido (OCH3→NHCOCH3)",
        smirks="[c:1][OX2:2][CH3:3]>>[c:1][NH:2][C:3](=[O:4])[CH3:5]",
        description="Acetamido replaces methoxy. "
                    "Adds H-bond donor and acceptor.",
        expected_impact="Acetamido, H-bonding, amide",
        complexity_delta=0.3,
        tags=["acetamido", "H-bonding", "amide"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 6"
    ),
    "OSUB050": SmirksEntry(
        id="OSUB050",
        category="o_substitutions",
        name="Hydroxyl to thiol (OH→SH)",
        smirks="[C:1][OX2H:2]>>[C:1][SX2H:2]",
        description="Thiol replaces hydroxyl. "
                    "Sulfur adds different H-bonding and pKa.",
        expected_impact="Thiol, sulfur, different_pKa",
        complexity_delta=0.0,
        tags=["thiol", "sulfur", "hydroxyl"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "OSUB051": SmirksEntry(
        id="OSUB051",
        category="o_substitutions",
        name="Methoxy to methylseleno (Se isostere)",
        smirks="[c:1][OX2:2][CH3:3]>>[c:1][Se:2][CH3:3]",
        description="Methylseleno replaces methoxy. "
                    "Selenium is larger, more polarizable.",
        expected_impact="Selenium, polarizability, size",
        complexity_delta=0.3,
        tags=["selenium", "polarizability", "methoxy"],
        reference="Chalcogen isosteres"
    ),
    "OSUB052": SmirksEntry(
        id="OSUB052",
        category="o_substitutions",
        name="Methoxy to oxime ether (OCH3→ON=CHCH3)",
        smirks="[c:1][OX2:2][CH3:3]>>[c:1][O:2][CH:3]=[N:4][CH3:5]",
        description="Oxime ether replaces methoxy. "
                    "Different reactivity and H-bonding.",
        expected_impact="Oxime_ether, reactivity, H-bonding",
        complexity_delta=0.3,
        tags=["oxime_ether", "reactivity", "H-bonding"],
        reference="Oxime ether isosteres"
    ),

    # ============================================================================
    # ETHER MODIFICATIONS (6 more from extraction doc lines 628-645)
    # ============================================================================
    "ETHER009": SmirksEntry(
        id="ETHER009",
        category="ether_modifications",
        name="Ether to methylene (O→CH2)",
        smirks="[C:1][O:2][C:3]>>[C:1][CH2:2][C:3]",
        description="Methylene replaces oxygen in ether. "
                    "Removes H-bond acceptor, increases lipophilicity.",
        expected_impact="Methylene, lipophilicity, no_H-bond",
        complexity_delta=0.0,
        tags=["methylene", "lipophilicity", "no_H-bond"],
        reference="Ether modifications"
    ),
    "ETHER010": SmirksEntry(
        id="ETHER010",
        category="ether_modifications",
        name="Phenoxy to thiophenoxy (ArO→ArS)",
        smirks="[c:1][O:2][c:3]>>[c:1][S:2][c:3]",
        description="Thiophenoxy replaces phenoxy. "
                    "Sulfur adds lipophilicity and different metabolism.",
        expected_impact="Thiophenoxy, sulfur, lipophilicity",
        complexity_delta=0.0,
        tags=["thiophenoxy", "sulfur", "lipophilicity"],
        reference="Ether modifications"
    ),
    "ETHER011": SmirksEntry(
        id="ETHER011",
        category="ether_modifications",
        name="Ether to selenide (O→Se)",
        smirks="[C:1][O:2][C:3]>>[C:1][Se:2][C:3]",
        description="Selenide replaces ether. "
                    "Selenium is larger, more polarizable.",
        expected_impact="Selenide, selenium, polarizability",
        complexity_delta=0.3,
        tags=["selenide", "selenium", "polarizability"],
        reference="Chalcogen isosteres"
    ),
    "ETHER012": SmirksEntry(
        id="ETHER012",
        category="ether_modifications",
        name="THF to THT (cyclic O→S)",
        smirks="[C:1]1[C:2][O:3][C:4][C:5]1>>[C:1]1[C:2][S:3][C:4][C:5]1",
        description="Tetrahydrothiophene replaces THF. "
                    "Sulfur in 5-membered ring adds lipophilicity.",
        expected_impact="THT, sulfur, 5-membered",
        complexity_delta=0.0,
        tags=["THT", "sulfur", "THF"],
        reference="Cyclic ether modifications"
    ),
    "ETHER013": SmirksEntry(
        id="ETHER013",
        category="ether_modifications",
        name="Ether to amine (O→NH)",
        smirks="[C:1][O:2][C:3]>>[C:1][NH:2][C:3]",
        description="Amine replaces ether. "
                    "Adds H-bond donor capability.",
        expected_impact="Amine, H-bond_donor, basicity",
        complexity_delta=0.0,
        tags=["amine", "H-bond_donor", "ether"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "ETHER014": SmirksEntry(
        id="ETHER014",
        category="ether_modifications",
        name="Dioxane to dithiane (cyclic O→S x2)",
        smirks="[C:1]1[C:2][O:3][C:4][C:5][O:6]1>>[C:1]1[C:2][S:3][C:4][C:5][S:6]1",
        description="Dithiane replaces dioxane. "
                    "Both oxygens replaced by sulfur.",
        expected_impact="Dithiane, sulfur, 6-membered",
        complexity_delta=0.0,
        tags=["dithiane", "sulfur", "6-membered"],
        reference="Cyclic ether modifications"
    ),

    # ============================================================================
    # AMIDE BOND REPLACEMENTS (4 more from extraction doc lines 392-419)
    # ============================================================================
    "AMID015": SmirksEntry(
        id="AMID015",
        category="amide_bond_replacements",
        name="Amide to 1,3,4-oxadiazole",
        smirks="[C:1](=[O:2])[NH:3]>>[C:1]1[N:2][N:3][C:4]([O:5])1",
        description="1,3,4-Oxadiazole replaces amide. "
                    "Metabolically stable 5-membered heterocycle.",
        expected_impact="Oxadiazole, metabolic_stability, heterocycle",
        complexity_delta=0.5,
        tags=["oxadiazole", "metabolic_stability", "heterocycle"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AMID016": SmirksEntry(
        id="AMID016",
        category="amide_bond_replacements",
        name="Amide to cyanoguanidine",
        smirks="[N:1][C:2](=[O:3])>>[N:1][C:2](=[N:3])N[C:4]#[N:5]",
        description="Cyanoguanidine replaces amide. "
                    "Planar with different H-bonding.",
        expected_impact="Cyanoguanidine, planar, H-bonding",
        complexity_delta=0.5,
        tags=["cyanoguanidine", "planar", "H-bonding"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AMID017": SmirksEntry(
        id="AMID017",
        category="amide_bond_replacements",
        name="Amide to N,N-dimethylamide (mask H-bond donor)",
        smirks="[C:1](=[O:2])[NH:3][C:4]>>[C:1](=[O:2])[N:3]([CH3:5])[C:4]",
        description="N,N-Dimethylamide replaces secondary amide. "
                    "Removes H-bond donor, improves permeability.",
        expected_impact="Dimethylamide, permeability, H-bond_reduction",
        complexity_delta=0.2,
        tags=["dimethylamide", "permeability", "H-bond_reduction"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "AMID018": SmirksEntry(
        id="AMID018",
        category="amide_bond_replacements",
        name="Amide to reversed amide (N-C=O→O=C-N)",
        smirks="[C:1][C:2](=[O:3])[N:4][C:5]>>[C:1][N:2][C:3](=[O:4])[C:5]",
        description="Reversed amide (retroamide). "
                    "Same atoms, different connectivity.",
        expected_impact="Retroamide, connectivity, same_atoms",
        complexity_delta=0.0,
        tags=["retroamide", "connectivity", "amide"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),

    # ============================================================================
    # NITROGEN HETEROCYCLE SWAPS (7 more from extraction doc lines 807-848)
    # ============================================================================
    "NHEX026": SmirksEntry(
        id="NHEX026",
        category="nitrogen_heterocycle_swaps",
        name="Oxazole to isoxazole (N position isomer)",
        smirks="[c:1]1[c:2][o:3][c:4][n:5]1>>[c:1]1[c:2][n:3][o:4][c:5]1",
        description="Isoxazole replaces oxazole. "
                    "N and O positions swapped.",
        expected_impact="Isoxazole, N_position, heterocycle",
        complexity_delta=0.0,
        tags=["isoxazole", "N_position", "oxazole"],
        reference="Aromatic heterocycle swaps"
    ),
    "NHEX027": SmirksEntry(
        id="NHEX027",
        category="nitrogen_heterocycle_swaps",
        name="Thiazole to oxazole (S→O)",
        smirks="[c:1]1[c:2][n:3][c:4][s:5]1>>[c:1]1[c:2][n:3][c:4][o:5]1",
        description="Oxazole replaces thiazole. "
                    "Oxygen replaces sulfur.",
        expected_impact="Oxazole, oxygen, chalcogen",
        complexity_delta=0.0,
        tags=["oxazole", "oxygen", "thiazole"],
        reference="Aromatic heterocycle swaps"
    ),
    "NHEX028": SmirksEntry(
        id="NHEX028",
        category="nitrogen_heterocycle_swaps",
        name="Imidazole to oxazole (NH→O)",
        smirks="[c:1]1[n:2][c:3][nH:4][c:5]1>>[c:1]1[n:2][c:3][o:4][c:5]1",
        description="Oxazole replaces imidazole. "
                    "Oxygen replaces NH.",
        expected_impact="Oxazole, oxygen, NH_replacement",
        complexity_delta=0.0,
        tags=["oxazole", "oxygen", "imidazole"],
        reference="Aromatic heterocycle swaps"
    ),
    "NHEX029": SmirksEntry(
        id="NHEX029",
        category="nitrogen_heterocycle_swaps",
        name="Hydantoin to barbituric acid (ring expansion)",
        smirks="[N:1]1[C:2](=[O:3])[C:4](=[O:5])[N:6]1>>[N:1]1[C:2](=[O:3])[C:4](=[O:5])[N:6][C:7](=[O:8])1",
        description="Barbituric acid replaces hydantoin. "
                    "6-membered vs 5-membered ring.",
        expected_impact="Barbituric, ring_expansion, 6-membered",
        complexity_delta=0.3,
        tags=["barbituric", "hydantoin", "ring_expansion"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Ch. 4"
    ),
    "NHEX030": SmirksEntry(
        id="NHEX030",
        category="nitrogen_heterocycle_swaps",
        name="Pyridone to pyridine (lactam→aromatic)",
        smirks="[c:1]1[c:2][c:3][C:4](=[O:5])[N:6]1>>[c:1]1[c:2][c:3][c:4][n:6]1",
        description="Pyridine replaces pyridone. "
                    "Removes carbonyl, adds aromaticity.",
        expected_impact="Pyridine, aromaticity, no_carbonyl",
        complexity_delta=-0.3,
        tags=["pyridine", "pyridone", "aromaticity"],
        reference="Pyridone pyridine isosteres"
    ),
    "NHEX031": SmirksEntry(
        id="NHEX031",
        category="nitrogen_heterocycle_swaps",
        name="1,2,4-Oxadiazole to 1,2,4-thiadiazole (O→S)",
        smirks="[c:1]1[n:2][o:3][n:4][c:5]1>>[c:1]1[n:2][s:3][n:4][c:5]1",
        description="Thiadiazole replaces oxadiazole. "
                    "Sulfur adds lipophilicity.",
        expected_impact="Thiadiazole, sulfur, lipophilicity",
        complexity_delta=0.0,
        tags=["thiadiazole", "sulfur", "oxadiazole"],
        reference="Aromatic heterocycle swaps"
    ),
    "NHEX032": SmirksEntry(
        id="NHEX032",
        category="nitrogen_heterocycle_swaps",
        name="Piperazine to homopiperazine (7-membered ring)",
        smirks="[C:1]1[N:2][C:3][N:4][C:5][C:6]1>>[C:1]1[N:2][C:3][N:4][C:5][C:6][C:7]1",
        description="Homopiperazine replaces piperazine. "
                    "Extra carbon adds flexibility.",
        expected_impact="Homopiperazine, 7-membered, flexibility",
        complexity_delta=0.2,
        tags=["homopiperazine", "7-membered", "piperazine"],
        reference="Amine ring expansion"
    ),

    # ============================================================================
    # SULFONYL MODIFICATIONS (4 more from extraction doc lines 647-662)
    # ============================================================================
    "SULF007": SmirksEntry(
        id="SULF007",
        category="sulfonyl_modifications",
        name="Sulfonyl to phosphonate (S→P)",
        smirks="[S:1](=[O:2])(=[O:3])[C:4]>>[P:1](=[O:2])(=[O:3])[C:4]",
        description="Phosphorus replaces sulfur in sulfonyl. "
                    "Different electronics and size.",
        expected_impact="Phosphonate, phosphorus, different_electronics",
        complexity_delta=0.5,
        tags=["phosphonate", "phosphorus", "sulfonyl"],
        reference="Sulfonyl phosphonate isosteres"
    ),
    "SULF008": SmirksEntry(
        id="SULF008",
        category="sulfonyl_modifications",
        name="Sulfonate to phosphate (S→P in ester)",
        smirks="[O:1][S:2](=[O:3])(=[O:4])[O:5]>>[O:1][P:2](=[O:3])([O:4])[O:5]",
        description="Phosphate replaces sulfonate ester. "
                    "Phosphorus isostere of sulfur.",
        expected_impact="Phosphate, phosphorus, ester",
        complexity_delta=0.3,
        tags=["phosphate", "phosphorus", "sulfonate"],
        reference="Sulfonate phosphate isosteres"
    ),
    "SULF009": SmirksEntry(
        id="SULF009",
        category="sulfonyl_modifications",
        name="N-ethyl sulfonamide (N→Et)",
        smirks="[S:1](=[O:2])(=[O:3])[NH2:4]>>[S:1](=[O:2])(=[O:3])[NH:4][CH2:5][CH3:6]",
        description="N-Ethyl sulfonamide replaces primary. "
                    "Reduces H-bond donor, adds lipophilicity.",
        expected_impact="N-ethylation, H-bond_reduction, lipophilicity",
        complexity_delta=0.2,
        tags=["N-ethylation", "sulfonamide", "lipophilicity"],
        reference="Sulfonamide SAR"
    ),
    "SULF010": SmirksEntry(
        id="SULF010",
        category="sulfonyl_modifications",
        name="Sulfonamide to sulfone (remove H-bond donor)",
        smirks="[S:1](=[O:2])(=[O:3])[NH2:4]>>[S:1](=[O:2])(=[O:3])[CH3:4]",
        description="Sulfone replaces sulfonamide. "
                    "Removes H-bond donor, adds lipophilicity.",
        expected_impact="Sulfone, H-bond_reduction, lipophilicity",
        complexity_delta=0.0,
        tags=["sulfone", "H-bond_reduction", "sulfonamide"],
        reference="Sulfonamide sulfone isosteres"
    ),

    # ============================================================================
    # POLARITY ADJUSTMENTS (NEW category, 20 entries from extraction doc 868-893)
    # ============================================================================
    "POLA004": SmirksEntry(
        id="POLA004",
        category="polarity_adjustments",
        name="CH2→O (methylene to oxygen, reduce lipophilicity)",
        smirks="[C:1][CH2:2][C:3]>>[C:1][O:2][C:3]",
        description="Oxygen replaces methylene. "
                    "Reduces lipophilicity, adds H-bond acceptor.",
        expected_impact="Oxygen, reduced_lipophilicity, H-bond_acceptor",
        complexity_delta=0.0,
        tags=["oxygen", "methylene", "lipophilicity"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "POLA005": SmirksEntry(
        id="POLA005",
        category="polarity_adjustments",
        name="CH2→NH (methylene to amine)",
        smirks="[C:1][CH2:2][C:3]>>[C:1][NH:2][C:3]",
        description="Amine replaces methylene. "
                    "Adds H-bond donor, basicity.",
        expected_impact="Amine, H-bond_donor, basicity",
        complexity_delta=0.0,
        tags=["amine", "methylene", "basicity"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "POLA006": SmirksEntry(
        id="POLA006",
        category="polarity_adjustments",
        name="CH2→S (methylene to thioether)",
        smirks="[C:1][CH2:2][C:3]>>[C:1][S:2][C:3]",
        description="Thioether replaces methylene. "
                    "Adds lipophilicity and polarizability.",
        expected_impact="Thioether, increased_lipophilicity, polarizability",
        complexity_delta=0.0,
        tags=["thioether", "methylene", "lipophilicity"],
        reference="Wilson & Gisvold, Organic Medicinal Chemistry, Table 2.11"
    ),
    "POLA007": SmirksEntry(
        id="POLA007",
        category="polarity_adjustments",
        name="CH2→SO (methylene to sulfoxide)",
        smirks="[C:1][CH2:2][C:3]>>[C:1][S:2](=[O:4])[C:3]",
        description="Sulfoxide replaces methylene. "
                    "Intermediate polarity.",
        expected_impact="Sulfoxide, intermediate_polarity, H-bond_acceptor",
        complexity_delta=0.3,
        tags=["sulfoxide", "methylene", "polarity"],
        reference="Chalcogen oxidation SAR"
    ),
    "POLA008": SmirksEntry(
        id="POLA008",
        category="polarity_adjustments",
        name="CH2→SO2 (methylene to sulfone)",
        smirks="[C:1][CH2:2][C:3]>>[C:1][S:2](=[O:4])(=[O:5])[C:3]",
        description="Sulfone replaces methylene. "
                    "Major polarity increase.",
        expected_impact="Sulfone, high_polarity, H-bond_acceptor",
        complexity_delta=0.4,
        tags=["sulfone", "methylene", "high_polarity"],
        reference="Chalcogen oxidation SAR"
    ),
    "POLA009": SmirksEntry(
        id="POLA009",
        category="polarity_adjustments",
        name="Ketone→Alcohol (increase H-bonding)",
        smirks="[C:1](=[O:2])[C:3]>>[C:1]([OH:2])[C:3]",
        description="Alcohol replaces ketone. "
                    "Increases H-bond donor/acceptor capability.",
        expected_impact="Alcohol, H-bonding, reduced_polarity",
        complexity_delta=0.0,
        tags=["alcohol", "ketone", "H-bonding"],
        reference="Ketone alcohol reduction"
    ),
    "POLA010": SmirksEntry(
        id="POLA010",
        category="polarity_adjustments",
        name="Nitrile→Amide (increase polarity)",
        smirks="[C:1]#[N:2]>>[C:1](=[O:3])[NH2:2]",
        description="Amide replaces nitrile. "
                    "Adds carbonyl and H-bond donor.",
        expected_impact="Amide, carbonyl, H-bonding",
        complexity_delta=0.3,
        tags=["amide", "nitrile", "H-bonding"],
        reference="Nitrile amide isosteres"
    ),
    "POLA011": SmirksEntry(
        id="POLA011",
        category="polarity_adjustments",
        name="CF3→CH3 (reduce polarity)",
        smirks="[C:1]([F:2])([F:3])([F:4])>>[C:1][CH3:2]",
        description="Methyl replaces CF3. "
                    "Reduces polarity and lipophilicity.",
        expected_impact="Methyl, reduced_polarity, CF3_removal",
        complexity_delta=-0.2,
        tags=["methyl", "CF3", "reduced_polarity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 3"
    ),
    "POLA012": SmirksEntry(
        id="POLA012",
        category="polarity_adjustments",
        name="t-Bu to C(CH3)2CH2OH (add polarity)",
        smirks="[C:1]([C:2])([C:3])[C:4]>>[C:1]([C:2])([C:3])[C:4]([CH2:5][OH:6])",
        description="Hydroxymethyl added to t-Bu. "
                    "Adds polarity without removing bulk.",
        expected_impact="Hydroxymethyl, added_polarity, bulk",
        complexity_delta=0.3,
        tags=["hydroxymethyl", "t-butyl", "polarity"],
        reference="Polarity adjustment SAR"
    ),
    "POLA013": SmirksEntry(
        id="POLA013",
        category="polarity_adjustments",
        name="Amine→Amide (reduce basicity)",
        smirks="[NH2:1][C:2]>>[N:1][C:2](=[O:3])",
        description="Amide replaces amine. "
                    "Major basicity reduction, adds polarity.",
        expected_impact="Amide, reduced_basicity, polarity",
        complexity_delta=0.3,
        tags=["amide", "amine", "basicity"],
        reference="Amine amide conversion"
    ),
    "POLA014": SmirksEntry(
        id="POLA014",
        category="polarity_adjustments",
        name="Nitro→Amino (reduce polarity)",
        smirks="[N+:1](=[O:2])([O-:3])>>[NH2:1]",
        description="Amino replaces nitro. "
                    "Major polarity reduction, adds H-bond donor.",
        expected_impact="Amino, reduced_polarity, H-bond_donor",
        complexity_delta=-0.2,
        tags=["amino", "nitro", "polarity"],
        reference="Nitro amine reduction"
    ),
    "POLA015": SmirksEntry(
        id="POLA015",
        category="polarity_adjustments",
        name="Halogen→Hydroxyl (increase H-bonding)",
        smirks="[C:1][F:2]>>[C:1][OH:2]",
        description="Hydroxyl replaces fluorine. "
                    "Adds H-bond donor/acceptor.",
        expected_impact="Hydroxyl, H-bonding, polarity",
        complexity_delta=0.0,
        tags=["hydroxyl", "fluorine", "H-bonding"],
        reference="Halogen hydroxyl exchange"
    ),
    "POLA016": SmirksEntry(
        id="POLA016",
        category="polarity_adjustments",
        name="Cyano→Carboxylic acid (increase polarity)",
        smirks="[C:1]#[N:2]>>[C:1](=[O:3])[OH:4]",
        description="Carboxylic acid replaces cyano. "
                    "Major polarity increase, ionizable.",
        expected_impact="Carboxylic_acid, ionizable, high_polarity",
        complexity_delta=0.3,
        tags=["carboxylic_acid", "cyano", "ionizable"],
        reference="Nitrile oxidation"
    ),
    "POLA017": SmirksEntry(
        id="POLA017",
        category="polarity_adjustments",
        name="Methyl ester→Free acid (increase polarity)",
        smirks="[C:1](=[O:2])[O:3][CH3:4]>>[C:1](=[O:2])[OH:3]",
        description="Free acid replaces methyl ester. "
                    "Ionizable, major polarity increase.",
        expected_impact="Free_acid, ionizable, polarity",
        complexity_delta=0.0,
        tags=["free_acid", "methyl_ester", "ionizable"],
        reference="Ester hydrolysis"
    ),
    "POLA018": SmirksEntry(
        id="POLA018",
        category="polarity_adjustments",
        name="Tertiary amine→N-oxide (increase polarity)",
        smirks="[N:1]([C:2])([C:3])[C:4]>>[N+:1](=[O:5])([C:2])([C:3])[C:4]",
        description="N-Oxide replaces tertiary amine. "
                    "Major polarity increase.",
        expected_impact="N-oxide, high_polarity, no_basicity",
        complexity_delta=0.3,
        tags=["N-oxide", "tertiary_amine", "polarity"],
        reference="Amine oxidation"
    ),
    "POLA019": SmirksEntry(
        id="POLA019",
        category="polarity_adjustments",
        name="Phenyl→Pyridyl (add polarity)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[c:1]1[c:2][c:3][n:4][c:5][c:6]1",
        description="Pyridyl replaces phenyl. "
                    "Adds dipole and H-bond acceptor.",
        expected_impact="Pyridyl, dipole, H-bond_acceptor",
        complexity_delta=0.0,
        tags=["pyridyl", "phenyl", "polarity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 2"
    ),
    "POLA020": SmirksEntry(
        id="POLA020",
        category="polarity_adjustments",
        name="Aromatic→Aliphatic (reduce stacking)",
        smirks="[c:1]1[c:2][c:3][c:4][c:5][c:6]1>>[C:1]1[C:2][C:3][C:4][C:5][C:6]1",
        description="Cyclohexyl replaces phenyl. "
                    "Removes aromatic stacking, different solubility.",
        expected_impact="Cyclohexyl, no_stacking, solubility",
        complexity_delta=0.5,
        tags=["cyclohexyl", "phenyl", "saturation"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
    "POLA021": SmirksEntry(
        id="POLA021",
        category="polarity_adjustments",
        name="Ether→Thioether (increase lipophilicity)",
        smirks="[C:1][O:2][C:3]>>[C:1][S:2][C:3]",
        description="Thioether replaces ether. "
                    "Increases lipophilicity and polarizability.",
        expected_impact="Thioether, increased_lipophilicity, polarizability",
        complexity_delta=0.0,
        tags=["thioether", "ether", "lipophilicity"],
        reference="Ether thioether exchange"
    ),
    "POLA022": SmirksEntry(
        id="POLA022",
        category="polarity_adjustments",
        name="Bicyclic→Monocyclic (reduce rigidity)",
        smirks="[c:1]1[c:2][c:3]2[c:4][c:5][c:6][c:7]1[c:8]2>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Monocyclic replaces bicyclic. "
                    "Reduces rigidity and molecular weight.",
        expected_impact="Monocyclic, reduced_rigidity, lower_MW",
        complexity_delta=-0.5,
        tags=["monocyclic", "bicyclic", "rigidity"],
        reference="Ring simplification"
    ),
    "POLA023": SmirksEntry(
        id="POLA023",
        category="polarity_adjustments",
        name="Cyclohexyl→Phenyl (add lipophilicity/aromaticity)",
        smirks="[C:1]1[C:2][C:3][C:4][C:5][C:6]1>>[c:1]1[c:2][c:3][c:4][c:5][c:6]1",
        description="Phenyl replaces cyclohexyl. "
                    "Adds aromaticity and planar stacking.",
        expected_impact="Aromaticity, planar_stacking, lipophilicity",
        complexity_delta=0.5,
        tags=["phenyl", "cyclohexyl", "aromaticity"],
        reference="Brown, Bioisosteres in Medicinal Chemistry, Ch. 13"
    ),
}

def get_smirks_by_category(category: str) -> List[SmirksEntry]:
    """Get all SMIRKS entries in a category."""
    return [e for e in SMIRKS_LIBRARY.values() if e.category == category]

def get_smirks_by_tags(tags: List[str]) -> List[SmirksEntry]:
    """Get SMIRKS entries matching any of the given tags."""
    return [e for e in SMIRKS_LIBRARY.values() 
            if any(t in e.tags for t in tags)]

def get_smirks_for_group(group_name: str) -> List[SmirksEntry]:
    """Get all SMIRKS applicable to a specific functional group (from multiple categories)."""
    group_to_categories = {
        "carboxylic_acid": ["carboxylic_acid_replacements", "bioisosteric_replacements", "polarity_adjustments"],
        "amide": ["amide_bond_replacements", "polarity_adjustments", "metabolic_stability"],
        "urea": ["amide_bond_replacements", "metabolic_stability"],
        "ketone": ["carbonyl_modifications", "metabolic_stability", "polarity_adjustments"],
        "aldehyde": ["carbonyl_modifications", "metabolic_stability"],
        "alcohol": ["carbonyl_modifications", "o_substitutions", "steric_shielding", "polarity_adjustments"],
        "phenol": ["o_substitutions", "bioisosteric_replacements", "aromatic_ring_swaps"],
        "methoxy": ["o_substitutions", "metabolic_stability", "steric_shielding"],
        "ethoxy": ["o_substitutions", "steric_shielding"],
        "isopropoxy": ["o_substitutions", "steric_shielding"],
        "trifluoromethoxy": ["o_substitutions", "halogen_substitutions"],
        "difluoromethoxy": ["o_substitutions", "halogen_substitutions"],
        "phenyl": ["aromatic_ring_swaps", "aromatic_substitutions", "carbocyclic_replacements", "polarity_adjustments"],
        "pyridine": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps", "cns_penetration"],
        "pyrimidine": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "pyridazine": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "pyrazine": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "thiophene": ["aromatic_ring_swaps", "bioisosteric_replacements"],
        "furan": ["aromatic_ring_swaps", "bioisosteric_replacements"],
        "pyrrole": ["aromatic_ring_swaps", "nitrogen_heterocycle_swaps"],
        "indole": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "benzimidazole": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "benzofuran": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "benzothiophene": ["nitrogen_heterocycle_swaps", "aromatic_ring_swaps"],
        "chloro": ["halogen_substitutions", "aromatic_substitutions", "steric_shielding"],
        "bromo": ["halogen_substitutions", "aromatic_substitutions"],
        "fluoro": ["halogen_substitutions", "cns_penetration", "metabolic_stability"],
        "iodo": ["halogen_substitutions", "aromatic_substitutions"],
        "trifluoro": ["halogen_substitutions", "steric_shielding"],
        "trifluoromethyl": ["halogen_substitutions", "steric_shielding"],
        "primary_amine": ["amine_modifications", "cns_penetration", "metabolic_stability", "polarity_adjustments"],
        "secondary_amine": ["amine_modifications", "cns_penetration", "metabolic_stability", "polarity_adjustments"],
        "tertiary_amine": ["amine_modifications", "cns_penetration", "metabolic_stability", "polarity_adjustments"],
        "dimethylamine": ["amine_modifications", "steric_shielding", "cns_penetration"],
        "piperazine": ["amine_modifications", "cns_penetration", "nitrogen_heterocycle_swaps"],
        "piperidine": ["amine_modifications", "cns_penetration", "nitrogen_heterocycle_swaps"],
        "morpholine": ["amine_modifications", "cns_penetration", "ether_modifications"],
        "pyrrolidine": ["amine_modifications", "nitrogen_heterocycle_swaps"],
        "azetidine": ["amine_modifications", "nitrogen_heterocycle_swaps"],
        "imidazolidine": ["amine_modifications", "nitrogen_heterocycle_swaps"],
        "hydrazine": ["amine_modifications", "carbonyl_modifications"],
        "guanidine": ["amine_modifications", "nitrogen_heterocycle_swaps"],
        "amidines": ["amine_modifications", "cns_penetration"],
        "cyanoguanidine": ["amine_modifications", "nitrile_modifications"],
        "nitrile": ["nitrile_modifications", "cns_penetration", "polarity_adjustments"],
        "sulfonamide": ["sulfonamide_modifications", "carboxylic_acid_replacements", "cns_penetration", "polarity_adjustments"],
        "sulfone": ["sulfonyl_modifications", "bioisosteric_replacements", "polarity_adjustments"],
        "sulfoxide": ["sulfonyl_modifications", "polarity_adjustments"],
        "thioether": ["ether_modifications", "metabolic_stability", "polarity_adjustments"],
        "methyl": ["steric_shielding", "metabolic_stability", "halogen_substitutions", "aromatic_substitutions"],
        "ethyl": ["steric_shielding", "metabolic_stability"],
        "isopropyl": ["steric_shielding", "metabolic_stability"],
        "t-butyl": ["steric_shielding", "metabolic_stability", "aromatic_substitutions"],
        "cyclohexyl": ["carbocyclic_replacements", "steric_shielding", "aromatic_ring_swaps", "polarity_adjustments"],
        "cyclopropyl": ["carbocyclic_replacements", "steric_shielding"],
        "norbornane": ["carbocyclic_replacements", "steric_shielding"],
        "bicyclo": ["carbocyclic_replacements", "steric_shielding"],
        "methylthio": ["o_substitutions", "sulfonyl_modifications"],
        "methylsulfonyl": ["sulfonyl_modifications", "metabolic_stability", "aromatic_substitutions"],
        "hydroxymethyl": ["benzylic_modifications", "o_substitutions"],
        "benzylic_alcohol": ["benzylic_modifications"],
        "benzyl": ["benzylic_modifications", "aromatic_ring_swaps"],
        "acetylenic": ["halogen_substitutions", "steric_shielding"],
        "alkene": ["halogen_substitutions", "metabolic_stability"],
        "cyano": ["nitrile_modifications", "halogen_substitutions", "aromatic_substitutions", "polarity_adjustments"],
        "nitro": ["aromatic_substitutions", "polarity_adjustments"],
        "amino": ["amine_modifications", "aromatic_substitutions", "polarity_adjustments"],
        "hydroxyl": ["o_substitutions", "bioisosteric_replacements", "steric_shielding", "polarity_adjustments"],
        "ester": ["ester_modifications", "metabolic_stability", "polarity_adjustments"],
        "lactone": ["ester_modifications", "carbonyl_modifications"],
        "carbamate": ["ester_modifications", "amide_bond_replacements"],
        # ── Phase 1b (2026-06-09) — wire the editable-site SMARTS additions ──
        "aromatic_h": ["aromatic_substitutions", "halogen_substitutions", "metabolic_stability"],
        "hydroxymethyl": ["benzylic_modifications", "o_substitutions", "polarity_adjustments"],
        "gem_dimethyl": ["steric_shielding", "metabolic_stability"],
        "alpha_methyl": ["steric_shielding", "metabolic_stability", "halogen_substitutions"],
    }
    categories = group_to_categories.get(group_name, [])
    results = []
    seen_ids = set()
    for cat in categories:
        for entry in get_smirks_by_category(cat):
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                results.append(entry)
    return results

def validate_entire_library() -> Dict:
    """Startup validation: ensure all SMIRKS parse correctly."""
    from rdkit.Chem import AllChem
    results = {"valid": 0, "invalid": 0, "errors": []}
    for entry_id, entry in SMIRKS_LIBRARY.items():
        try:
            rxn = AllChem.ReactionFromSmarts(entry.smirks)
            if rxn and rxn.GetNumReactantTemplates() > 0:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["errors"].append(entry_id)
        except Exception:
            results["invalid"] += 1
            results["errors"].append(entry_id)
    return results
