from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Union
from enum import Enum

# ── Vision Agent Output ──────────────────────────────────────

class InteractionType(str, Enum):
    H_BOND_DONOR = "h_bond_donor"
    H_BOND_ACCEPTOR = "h_bond_acceptor"
    SALT_BRIDGE = "salt_bridge"
    PI_STACK = "pi_stack"
    HYDROPHOBIC = "hydrophobic"
    CATION_PI = "cation_pi"

class FunctionalGroupInteraction(BaseModel):
    """A single interaction identified by the Vision Agent.

    A group can contact multiple residues (e.g. one hydroxyl that donates
    an H-bond to ASN 244 AND accepts from GLU 291). `residues` is the
    authoritative list; `residue` is retained as a back-compat shim that
    always equals `residues[0]` when residues is non-empty.

    `atom_indices` are RDKit atom indices in the lead SMILES that this
    specific group instance covers. Without indices, a molecule with three
    hydroxyls cannot disambiguate which hydroxyl is restricted vs editable.
    """
    group_name: str = Field(..., description="e.g., 'amidine', 'carboxylic_acid', 'phenyl'")
    residue: Optional[str] = Field(default=None, description="Legacy single-residue field — equals residues[0] when residues is non-empty.")
    residues: List[str] = Field(default_factory=list, description="All contacting residues — e.g. ['ASN 244', 'GLU 291']")
    interaction_type: InteractionType = Field(default=InteractionType.HYDROPHOBIC)
    interaction_types: List[InteractionType] = Field(default_factory=list, description="All interaction types for this group, aligned with residues")
    confidence: float = Field(ge=0.0, le=1.0)
    atom_indices: List[int] = Field(default_factory=list, description="RDKit atom indices in the lead SMILES this group covers")

    @model_validator(mode='after')
    def _reconcile_residue_fields(self):
        # residues is the source of truth; backfill residue/interaction_type for legacy consumers
        if self.residues and not self.residue:
            self.residue = self.residues[0]
        elif self.residue and not self.residues:
            self.residues = [self.residue]
        if self.interaction_types and self.interaction_type == InteractionType.HYDROPHOBIC and len(self.interaction_types) > 0:
            self.interaction_type = self.interaction_types[0]
        elif self.interaction_type and not self.interaction_types:
            self.interaction_types = [self.interaction_type]
        return self

class ExposedGroup(BaseModel):
    """A functional group available for modification."""
    group_name: str = Field(..., description="e.g., 'methoxy', 'chloro', 'ethyl'")
    position_description: str = Field(..., description="e.g., 'para on ring 2'")
    atom_indices: List[int] = Field(default_factory=list, description="RDKit atom indices in the lead SMILES this group covers")

class VisionAgentOutput(BaseModel):
    """What the Vision Agent returns (group names, NOT raw SMARTS).

    Three orthogonal categories — a group belongs to EXACTLY one:
      - restricted_groups: makes a visible protein contact in the LID
      - structural_core_groups: defines chemotype but no protein contact
      - target_groups: editable optimization site (default if unclear)

    Keeping STRUCTURAL_CORE separate from RESTRICTED was the architectural
    fix for "single place optimizable except pharmacophore core" — the
    Vision Agent was conflating "binding-essential" with "structurally
    embedded" and dumping both into RESTRICTED, leaving ≤2 editable sites.

    `scaffold_atoms` are atom indices the vision agent flagged as part of
    the structural core — modifying them would change the scaffold identity.
    These are MERGED with RDKit's deterministic Bemis-Murcko atoms; either
    source can flag an atom.
    """
    restricted_groups: List[FunctionalGroupInteraction]
    structural_core_groups: List[ExposedGroup] = Field(default_factory=list, description="Groups that define the chemotype scaffold but make no protein contact")
    target_groups: List[ExposedGroup]
    overall_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    scaffold_atoms: List[int] = Field(default_factory=list, description="Vision-flagged scaffold atom indices (merged with Murcko scaffold)")

# ── SMARTS Builder Output ────────────────────────────────────

class SmartsMapping(BaseModel):
    """Python-generated SMARTS from group names."""
    restricted_smarts: str
    target_smarts: List[str]
    group_to_smarts: Dict[str, str]  # "amidine" -> "[NX3][CX3]=[NX2]"
    group_names: List[str] = []  # Names aligned with target_smarts indices

# ── Optimization Agent Output ────────────────────────────────

class SmirksStrategy(BaseModel):
    """A single bioisosteric replacement strategy."""
    site_index: int = Field(..., description="Index into target_smarts list")
    target_group_name: str
    smirks_id: str = Field(..., description="Reference ID into SMIRKS_LIBRARY")
    smirks: str = Field(..., description="Reaction SMARTS, e.g., [C:1](=O)[OH]>>[C:1]1=NN=N[NH]1")
    replacement_name: str = Field(..., description="e.g., 'tetrazole'")
    rationale: str
    predicted_impact: Union[str, float]
    confidence: float = Field(ge=0.0, le=1.0)
    rag_source: Optional[str] = None  # Which textbook chunk

class OptimizationAgentOutput(BaseModel):
    """What the Optimization Agent returns."""
    admet_goal: str
    expert_narrative: Optional[str] = None
    strategies: List[SmirksStrategy]

# ── Context Analysis Output (LLM Analyzer) ──────────────────

class EndpointPriority(BaseModel):
    endpoint: str           # e.g., "BBB_Martins"
    weight: float           # 0.0 to 1.0 (relative importance)
    direction: str          # "increase" or "reduce"
    reasoning: str          # Why this endpoint matters for this project
    clinical_context: str   # How this maps to the therapeutic goal

class ContextAnalysis(BaseModel):
    """Output of the LLM context analyzer."""
    endpoint_priorities: List[EndpointPriority]
    primary_optimization_goal: str       # Single-sentence goal
    therapeutic_constraints: List[str]   # Hard requirements from context
    scoring_rationale: str               # Why these weights were chosen
    hard_stops: Dict[str, float]         # Endpoints that should disqualify if exceeded

# ── Analog Record (Provenance) ───────────────────────────────

class FilterResults(BaseModel):
    valid_mol: bool = False
    sanitizes: bool = False
    pharmacophore_intact: bool = False
    sa_score_ok: bool = False
    lipinski_pass: bool = False
    pains_pass: bool = False
    brenk_pass: bool = False
    glaxo_pass: bool = False

class AnalogRecord(BaseModel):
    """Full provenance record for each generated analog."""
    smiles: str
    canonical_smiles: str
    lead_smiles: str
    modifications: List[str]          # Human-readable list
    smirks_applied: List[str]         # SMIRKS strings used
    agent_rationale: str
    rag_chunks_used: List[str]
    sa_score: float
    filter_results: FilterResults
    admet_results: Optional[Dict] = None
    pareto_rank: Optional[int] = None
    pareto_score: Optional[float] = None

# ── Pipeline Output ──────────────────────────────────────────

class ADMETLiability(BaseModel):
    endpoint: str
    value: float
    threshold: float
    goal: str
    direction: str  # "reduce" or "increase"

class LeadProfile(BaseModel):
    smiles: str
    admet_data: Dict
    liabilities: List[ADMETLiability]
    strengths: List[str]
    primary_goal: str

class OptimizationResult(BaseModel):
    lead_profile: LeadProfile
    total_strategies: int
    total_analogs_generated: int
    total_passed_prefilter: int
    total_passed_admet: int
    top_analogs: List[AnalogRecord]
    diversity_clusters: int
    report_pdf_path: Optional[str] = None
    sdf_path: Optional[str] = None
    iterations_used: int
    errors: List[str]
    used_lid: bool = False
    secondary_targets: List[Dict] = []
    search_space_size: int = 0
    methodology_notes: str = ""
