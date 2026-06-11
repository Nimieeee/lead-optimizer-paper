#!/usr/bin/env python3
"""
Experiment 1 — MMP recovery rate

For each matched molecular pair (A, B) where B is a documented improving
analog of A, apply the platform's 479-entry SMIRKS library to A and ask
whether B appears among the generated analogs.

Reports recall@K for K in {1, 5, 10, 50, 100}, both by Tanimoto-to-B rank
and by exact canonical-SMILES match.

No LLM in the loop. The Vision Agent and Optimization Agent are stubbed
to "everything is TARGET" so this experiment isolates the SMIRKS engine
and the structural filters.

Run:
    paper/.venv/bin/python paper/experiments/exp1_mmp_recovery/run.py \
        --pairs paper/experiments/exp1_mmp_recovery/data/pilot_pairs.csv \
        --output paper/experiments/exp1_mmp_recovery/results/pilot
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

# ── Path injection to import the production SMIRKS library ──
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "backend"))

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, rdChemReactions
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")

from app.services.lead_optimizer.smirks_library import SMIRKS_LIBRARY  # noqa: E402


@dataclass
class PairResult:
    pair_id: str
    smiles_A: str
    smiles_B: str
    source: str
    transformation: str
    analogs_generated: int
    unique_analogs: int
    B_recovered_exact: bool
    B_rank_by_tanimoto: int | None
    best_tanimoto: float
    top10_tanimoto_mean: float
    smirks_that_recovered_B: list[str]
    runtime_s: float


# ──────────────────────────────────────────────────────────────
# Core RDKit helpers


def canonical(smi: str) -> str | None:
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def morgan_fp(mol, radius: int = 2, nbits: int = 2048):
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits)


def murcko_smiles(mol) -> str:
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────
# SMIRKS application


def apply_one_smirks(mol_A, smirks_str: str) -> list[str]:
    """Return canonical SMILES of all unique products."""
    try:
        rxn = rdChemReactions.ReactionFromSmarts(smirks_str)
    except Exception:
        return []
    if rxn is None:
        return []
    try:
        product_sets = rxn.RunReactants((mol_A,))
    except Exception:
        return []

    seen = set()
    for products in product_sets:
        for prod in products:
            try:
                Chem.SanitizeMol(prod)
            except Exception:
                continue
            smi = Chem.MolToSmiles(prod)
            if smi:
                seen.add(smi)
    return sorted(seen)


def generate_analogs(smiles_A: str) -> dict[str, list[str]]:
    """Apply every SMIRKS in the library. Return {canonical_smiles: [smirks_ids]}."""
    mol_A = Chem.MolFromSmiles(smiles_A)
    if mol_A is None:
        return {}
    out: dict[str, list[str]] = {}
    for sid, entry in SMIRKS_LIBRARY.items():
        for smi in apply_one_smirks(mol_A, entry.smirks):
            out.setdefault(smi, []).append(sid)
    return out


# ──────────────────────────────────────────────────────────────
# Per-pair evaluation


def evaluate_pair(pair: dict) -> PairResult:
    t0 = time.perf_counter()
    pair_id = pair["pair_id"]
    smiles_A = pair["smiles_A"].strip()
    smiles_B = pair["smiles_B"].strip()
    source = pair.get("source", "")
    transformation = pair.get("transformation", "")

    canon_B = canonical(smiles_B)
    mol_B = Chem.MolFromSmiles(smiles_B) if canon_B else None

    if mol_B is None:
        return PairResult(
            pair_id=pair_id,
            smiles_A=smiles_A,
            smiles_B=smiles_B,
            source=source,
            transformation=transformation,
            analogs_generated=0,
            unique_analogs=0,
            B_recovered_exact=False,
            B_rank_by_tanimoto=None,
            best_tanimoto=0.0,
            top10_tanimoto_mean=0.0,
            smirks_that_recovered_B=[],
            runtime_s=time.perf_counter() - t0,
        )

    fp_B = morgan_fp(mol_B)
    analog_map = generate_analogs(smiles_A)
    # Sort by Tanimoto desc
    scored = []
    for smi, sids in analog_map.items():
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        tan = DataStructs.TanimotoSimilarity(morgan_fp(mol), fp_B)
        scored.append((smi, sids, tan))
    scored.sort(key=lambda x: -x[2])

    rank_B = None
    smirks_that_recovered_B = []
    for rank, (smi, sids, tan) in enumerate(scored, start=1):
        if smi == canon_B:
            rank_B = rank
            smirks_that_recovered_B = sids
            break

    top10 = [tan for _, _, tan in scored[:10]]

    return PairResult(
        pair_id=pair_id,
        smiles_A=smiles_A,
        smiles_B=smiles_B,
        source=source,
        transformation=transformation,
        analogs_generated=sum(len(v) for v in analog_map.values()),
        unique_analogs=len(analog_map),
        B_recovered_exact=rank_B is not None,
        B_rank_by_tanimoto=rank_B,
        best_tanimoto=scored[0][2] if scored else 0.0,
        top10_tanimoto_mean=sum(top10) / len(top10) if top10 else 0.0,
        smirks_that_recovered_B=smirks_that_recovered_B,
        runtime_s=time.perf_counter() - t0,
    )


# ──────────────────────────────────────────────────────────────
# Aggregate


def recall_at_k(results: list[PairResult], ks: Iterable[int]) -> dict[int, float]:
    out = {}
    n = len(results)
    if n == 0:
        return {k: 0.0 for k in ks}
    for k in ks:
        hits = sum(
            1
            for r in results
            if r.B_recovered_exact and r.B_rank_by_tanimoto is not None and r.B_rank_by_tanimoto <= k
        )
        out[k] = hits / n
    return out


def summarize(results: list[PairResult]) -> dict:
    ks = [1, 5, 10, 50, 100, 500]
    recall = recall_at_k(results, ks)
    n = len(results)
    n_recovered = sum(1 for r in results if r.B_recovered_exact)
    smirks_hit_counter = Counter()
    for r in results:
        for sid in r.smirks_that_recovered_B:
            smirks_hit_counter[sid] += 1
    return {
        "n_pairs": n,
        "n_B_recovered_exact": n_recovered,
        "any_recovery_rate": n_recovered / n if n else 0.0,
        "recall_at_k": recall,
        "mean_analogs_per_pair": sum(r.analogs_generated for r in results) / n if n else 0.0,
        "mean_unique_per_pair": sum(r.unique_analogs for r in results) / n if n else 0.0,
        "mean_best_tanimoto": sum(r.best_tanimoto for r in results) / n if n else 0.0,
        "median_runtime_s": sorted(r.runtime_s for r in results)[n // 2] if n else 0.0,
        "smirks_recovery_counts": dict(smirks_hit_counter.most_common(20)),
    }


# ──────────────────────────────────────────────────────────────
# Manifest (git SHA, library hash, env)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(pairs_path: Path) -> dict:
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), text=True
        ).strip()
    except Exception:
        git_sha = "unknown"
    try:
        git_dirty = (
            subprocess.check_output(["git", "status", "--porcelain"], cwd=str(REPO), text=True).strip() != ""
        )
    except Exception:
        git_dirty = None
    import rdkit

    smirks_path = REPO / "backend/app/services/lead_optimizer/smirks_library.py"
    return {
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "rdkit_version": rdkit.__version__,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "smirks_library_file": str(smirks_path.relative_to(REPO)),
        "smirks_library_sha256": file_sha256(smirks_path),
        "smirks_library_entry_count": len(SMIRKS_LIBRARY),
        "pairs_input": str(pairs_path),
        "pairs_input_sha256": file_sha256(pairs_path),
    }


# ──────────────────────────────────────────────────────────────
# CLI


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    pairs = []
    with open(args.pairs, newline="") as f:
        for row in csv.DictReader(f):
            pairs.append(row)

    print(f"[exp1] loaded {len(pairs)} pairs from {args.pairs}", file=sys.stderr)
    print(f"[exp1] SMIRKS library entries: {len(SMIRKS_LIBRARY)}", file=sys.stderr)
    print(f"[exp1] running with {args.workers} workers", file=sys.stderr)

    t_start = time.perf_counter()
    if args.workers > 1:
        with mp.Pool(args.workers) as pool:
            results = pool.map(evaluate_pair, pairs)
    else:
        results = [evaluate_pair(p) for p in pairs]
    total_runtime = time.perf_counter() - t_start
    print(f"[exp1] runtime: {total_runtime:.1f}s ({total_runtime/len(pairs):.2f}s/pair)", file=sys.stderr)

    # Per-pair CSV
    out_per_pair = args.output / "per_pair.csv"
    with open(out_per_pair, "w", newline="") as f:
        if results:
            w = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
            w.writeheader()
            for r in results:
                d = asdict(r)
                d["smirks_that_recovered_B"] = ";".join(d["smirks_that_recovered_B"])
                d["top10_tanimoto_mean"] = round(d["top10_tanimoto_mean"], 4)
                d["best_tanimoto"] = round(d["best_tanimoto"], 4)
                d["runtime_s"] = round(d["runtime_s"], 4)
                w.writerow(d)

    # Summary JSON
    summ = summarize(results)
    summ["total_runtime_s"] = round(total_runtime, 2)
    with open(args.output / "summary.json", "w") as f:
        json.dump(summ, f, indent=2)

    # Manifest
    with open(args.output / "manifest.json", "w") as f:
        json.dump(manifest(args.pairs), f, indent=2)

    # Print headline
    print()
    print("=" * 64)
    print(f"  Pairs evaluated:           {summ['n_pairs']}")
    print(f"  B recovered (exact match): {summ['n_B_recovered_exact']}/{summ['n_pairs']}  "
          f"= {summ['any_recovery_rate']*100:.1f}%")
    print(f"  Mean unique analogs/pair:  {summ['mean_unique_per_pair']:.1f}")
    print(f"  Mean best Tanimoto:        {summ['mean_best_tanimoto']:.3f}")
    print("  Recall @ K:")
    for k, v in summ["recall_at_k"].items():
        print(f"    recall@{k:<4} = {v*100:5.1f}%")
    print("=" * 64)
    print(f"  Results written to {args.output}")


if __name__ == "__main__":
    main()
