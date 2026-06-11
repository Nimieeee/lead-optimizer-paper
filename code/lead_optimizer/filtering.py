from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Lipinski, FilterCatalog, MolFromSmarts
from typing import Dict, List, Tuple, Optional
import pandas as pd
import os
import logging

# Suppress ALL RDKit warnings
RDLogger.logger().setLevel(RDLogger.CRITICAL)
RDLogger.DisableLog('rdApp.*')

logger = logging.getLogger(__name__)

# Path to Glaxo alerts CSV (deployed with the codebase)
GLAXO_ALERTS_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 
    'data', 'medchem_knowledge', 'glaxo_structural_alerts.csv'
)

def check_lipinski(mol) -> Tuple[bool, Dict]:
    """Lipinski's Rule of 5. Returns (passes, details)."""
    mw = Descriptors.ExactMolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    
    violations = sum([mw > 500, logp > 5, hbd > 5, hba > 10])
    return violations == 0, {
        "mw": mw, "logp": logp, "hbd": hbd, "hba": hba,
        "violations": violations
    }

def check_pains(mol) -> bool:
    """PAINS filter. Returns True if molecule PASSES."""
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(params.FilterCatalogs.PAINS)
    catalog = FilterCatalog.FilterCatalog(params)
    return not catalog.HasMatch(mol)

def check_brenk(mol) -> bool:
    """Brenk filter. Returns True if molecule PASSES."""
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(params.FilterCatalogs.BRENK)
    catalog = FilterCatalog.FilterCatalog(params)
    return not catalog.HasMatch(mol)

_glaxo_cache = None

def _load_glaxo_alerts():
    global _glaxo_cache
    if _glaxo_cache is not None:
        return _glaxo_cache
    if not os.path.exists(GLAXO_ALERTS_PATH):
        logger.warning(f"Glaxo alerts not found at {GLAXO_ALERTS_PATH}")
        return None
    try:
        df = pd.read_csv(GLAXO_ALERTS_PATH)
        df['ROMol'] = df['smarts'].apply(MolFromSmarts)
        df = df.dropna(subset=['ROMol'])
        _glaxo_cache = df
        logger.info(f"Loaded {len(df)} Glaxo structural alerts")
        return df
    except Exception as e:
        logger.error(f"Failed to load Glaxo alerts: {e}")
        return None

def check_glaxo(mol, alerts_df=None) -> bool:
    """Glaxo structural alerts. Returns True if molecule PASSES."""
    if alerts_df is None:
        alerts_df = _load_glaxo_alerts()
    if alerts_df is None:
        return True  # No alerts file = skip this filter
    
    for _, row in alerts_df.iterrows():
        if row['ROMol'] is not None and mol.HasSubstructMatch(row['ROMol']):
            return False
    return True

def run_prefilter(smiles: str) -> Tuple[bool, Dict]:
    """Run the full filtering cascade on a single molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, {"error": "Invalid SMILES"}
    
    lipinski_ok, lipinski_details = check_lipinski(mol)
    pains_ok = check_pains(mol)
    brenk_ok = check_brenk(mol)
    glaxo_ok = check_glaxo(mol)
    
    results = {
        "lipinski_pass": lipinski_ok,
        "lipinski_details": lipinski_details,
        "pains_pass": pains_ok,
        "brenk_pass": brenk_ok,
        "glaxo_pass": glaxo_ok,
    }
    
    passes_all = lipinski_ok and pains_ok and brenk_ok and glaxo_ok
    return passes_all, results

def batch_prefilter(smiles_list: List[str]) -> List[Tuple[str, bool, Dict]]:
    """Run pre-filter on a batch of SMILES."""
    _load_glaxo_alerts()
    
    results = []
    for smi in smiles_list:
        passes, details = run_prefilter(smi)
        results.append((smi, passes, details))
    
    passed = sum(1 for _, p, _ in results if p)
    total = len(smiles_list)
    if total > 0:
        logger.info(f"Pre-filter: {passed}/{total} passed ({passed/total*100:.1f}%)")
    return results
