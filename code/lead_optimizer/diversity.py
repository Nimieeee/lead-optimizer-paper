"""
Chemical diversity analysis using Morgan fingerprints + Butina clustering.
"""

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, DataStructs
from rdkit.ML.Cluster import Butina
from typing import List, Dict, Tuple
import logging
import numpy as np

# Suppress ALL RDKit warnings
RDLogger.logger().setLevel(RDLogger.CRITICAL)
RDLogger.DisableLog('rdApp.*')

logger = logging.getLogger(__name__)

def calculate_diversity_metrics(
    smiles_list: List[str],
    lead_smiles: str,
    radius: int = 2,
    nbits: int = 2048
) -> Dict:
    """
    Calculate chemical diversity metrics for a set of analogs.
    """
    mols = [Chem.MolFromSmiles(s) for s in smiles_list]
    lead_mol = Chem.MolFromSmiles(lead_smiles)
    
    valid_indices = [i for i, m in enumerate(mols) if m is not None]
    valid_mols = [mols[i] for i in valid_indices]
    
    if not valid_mols:
        return {}

    fps = [AllChem.GetMorganFingerprintAsBitVect(m, radius, nbits) for m in valid_mols]
    lead_fp = AllChem.GetMorganFingerprintAsBitVect(lead_mol, radius, nbits)
    
    # Tanimoto to lead
    tani_to_lead = [DataStructs.TanimotoSimilarity(fp, lead_fp) for fp in fps]
    
    # Pairwise Tanimoto (for clustering)
    n = len(fps)
    dists = []
    for i in range(1, n):
        for j in range(i):
            sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
            dists.append(1.0 - sim)
    
    # Butina clustering
    if n > 1:
        clusters = Butina.ClusterData(dists, n, 0.4, isDistData=True)
    else:
        clusters = [(0,)]
        
    cluster_sizes = sorted([len(c) for c in clusters], reverse=True)
    
    # Diversity score
    diversity_score = len(clusters) / max(n, 1)
    
    return {
        "mean_tanimoto_to_lead": float(np.mean(tani_to_lead)),
        "mean_pairwise_distance": float(np.mean(dists)) if dists else 0.0,
        "num_clusters": len(clusters),
        "cluster_sizes": cluster_sizes[:20],
        "diversity_score": min(diversity_score, 1.0),
        "tanimoto_to_lead": tani_to_lead,
        "cluster_assignments": clusters,
    }

def select_diverse_representatives(
    analogs: List[Dict],
    lead_smiles: str,
    max_per_cluster: int = 5
) -> List[Dict]:
    """
    Select the best analogs from each diversity cluster.
    """
    if not analogs:
        return []
        
    smiles_list = [a["smiles"] for a in analogs]
    metrics = calculate_diversity_metrics(smiles_list, lead_smiles)
    if not metrics:
        return analogs

    clusters = metrics["cluster_assignments"]
    
    selected = []
    for cluster in clusters:
        cluster_analogs = [analogs[i] for i in cluster if i < len(analogs)]
        # Sort by Pareto score descending
        cluster_analogs.sort(
            key=lambda a: a.get("pareto_score", 0.0),
            reverse=True
        )
        selected.extend(cluster_analogs[:max_per_cluster])
    
    # CRITICAL FIX: Re-sort selected analogs by pareto_score descending
    # so display order matches rank numbers
    selected.sort(key=lambda a: a.get("pareto_score", 0.0), reverse=True)
    
    # Re-assign ranks to match array order
    for i, analog in enumerate(selected):
        analog["pareto_rank"] = i + 1
    
    logger.info(f"Diversity selection: {len(selected)} reps from {len(clusters)} clusters")
    return selected
