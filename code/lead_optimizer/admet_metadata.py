"""
ADMET Metadata — Single Source of Truth for endpoint directions and thresholds.
"""

ADMET_METADATA = {
    # Absorption (high is good)
    "HIA_Hou": {"threshold": 0.5, "direction": "increase", "label": "Absorption (HIA)"},
    "Caco2_Wang": {"threshold": -5.0, "direction": "increase", "label": "Permeability (Caco2)"},
    "BBB_Martins": {"threshold": 0.5, "direction": "increase", "label": "BBB Penetration"},
    "Bioavailability_Ma": {"threshold": 0.5, "direction": "increase", "label": "Bioavailability"},
    
    # Physicochemical (range-based)
    "logP": {"min": 0, "max": 5.0, "direction": "reduce", "label": "Lipophilicity"},
    "molecular_weight": {"min": 150, "max": 500, "direction": "reduce", "label": "Mol Weight"},
    "tpsa": {"min": 20, "max": 140, "direction": "reduce", "label": "PSA"},
    
    # Toxicity (low is good)
    "hERG": {"threshold": 0.4, "direction": "reduce", "label": "hERG Risk"},
    "AMES": {"threshold": 0.4, "direction": "reduce", "label": "Ames Risk"},
    "DILI": {"threshold": 0.4, "direction": "reduce", "label": "Liver Injury Risk"},
    
    # Metabolism (low is good for inhibition)
    "CYP2D6_Veith": {"threshold": 0.5, "direction": "reduce", "label": "CYP2D6 Inhibition"},
    "CYP3A4_Veith": {"threshold": 0.5, "direction": "reduce", "label": "CYP3A4 Inhibition"},
    "CYP1A2_Veith": {"threshold": 0.5, "direction": "reduce", "label": "CYP1A2 Inhibition"},
}

def get_endpoint_direction(endpoint: str) -> str:
    """Return 'increase' or 'reduce' for a given endpoint."""
    meta = ADMET_METADATA.get(endpoint, {})
    return meta.get("direction", "reduce") # Default to reduce for safety
