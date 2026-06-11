#!/usr/bin/env python3
"""
Experiment 2, Scaffold preservation + structural-alert audit

For each lead in seed_leads.csv:
  1. Apply the full SMIRKS library to generate analogs
  2. Per analog, compute:
       - Bemis-Murcko scaffold (preserved vs lead?)
       - PAINS flag (RDKit FilterCatalog, all 3 PAINS sets)
       - Brenk flag (RDKit FilterCatalog Brenk)
       - Lipinski Ro5 violations
       - Heavy-atom count delta
       - cLogP delta
  3. Two filter-strength conditions:
       - "default" : keep analogs where Bemis-Murcko scaffold preserved (soft gate proxy)
       - "ablation_no_gate" : keep all analogs (the Murcko gate disabled)

Aggregate metrics per filter-condition and per therapeutic class.

Pure RDKit; no LLM in the loop.
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
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "backend"))

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Crippen, Descriptors, Lipinski, rdChemReactions
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")

from app.services.lead_optimizer.smirks_library import SMIRKS_LIBRARY  # noqa: E402


# ───── PAINS / Brenk filter setup (process-local cache) ─────
_FILTERS = {}


def _filters():
    """Lazily build PAINS + Brenk filter catalogs once per process."""
    if _FILTERS:
        return _FILTERS
    p_params = FilterCatalogParams()
    p_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_A)
    p_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_B)
    p_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_C)
    _FILTERS["pains"] = FilterCatalog(p_params)
    b_params = FilterCatalogParams()
    b_params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
    _FILTERS["brenk"] = FilterCatalog(b_params)
    return _FILTERS


def has_pains(mol) -> bool:
    return _filters()["pains"].HasMatch(mol)


def has_brenk(mol) -> bool:
    return _filters()["brenk"].HasMatch(mol)


# ───── Per-mol metric computation ─────


def murcko(mol) -> str:
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
    except Exception:
        return ""


def lipinski_violations(mol) -> int:
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    v = 0
    if mw > 500:
        v += 1
    if logp > 5:
        v += 1
    if hbd > 5:
        v += 1
    if hba > 10:
        v += 1
    return v


# ───── SMIRKS enumeration ─────


def apply_one_smirks(mol_A, smirks_str: str) -> list[str]:
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


def enumerate_analogs(seed_smiles: str) -> dict[str, list[str]]:
    """Apply every SMIRKS; return {canonical_smiles: [smirks_ids]}."""
    mol = Chem.MolFromSmiles(seed_smiles)
    if mol is None:
        return {}
    out: dict[str, list[str]] = {}
    for sid, entry in SMIRKS_LIBRARY.items():
        for smi in apply_one_smirks(mol, entry.smirks):
            out.setdefault(smi, []).append(sid)
    return out


# ───── Per-seed driver ─────


def evaluate_seed(row: dict) -> dict:
    t0 = time.perf_counter()
    seed_id = row["seed_id"]
    smiles = row["smiles"].strip()
    name = row["name"]
    tclass = row.get("therapeutic_class", "")

    mol_seed = Chem.MolFromSmiles(smiles)
    if mol_seed is None:
        return {
            "seed_id": seed_id,
            "name": name,
            "therapeutic_class": tclass,
            "error": "invalid_seed_smiles",
            "n_analogs": 0,
            "runtime_s": time.perf_counter() - t0,
        }

    seed_scaffold = murcko(mol_seed)
    seed_ha = mol_seed.GetNumHeavyAtoms()
    seed_logp = Crippen.MolLogP(mol_seed)

    analog_map = enumerate_analogs(smiles)

    # Per-analog metrics
    rows = []
    for analog_smi in analog_map:
        mol = Chem.MolFromSmiles(analog_smi)
        if mol is None:
            continue
        scaffold = murcko(mol)
        rows.append(
            {
                "seed_id": seed_id,
                "analog_smiles": analog_smi,
                "n_smirks_producing_it": len(analog_map[analog_smi]),
                "scaffold_preserved": scaffold == seed_scaffold,
                "has_pains": has_pains(mol),
                "has_brenk": has_brenk(mol),
                "lipinski_violations": lipinski_violations(mol),
                "heavy_atom_delta": mol.GetNumHeavyAtoms() - seed_ha,
                "logp_delta": round(Crippen.MolLogP(mol) - seed_logp, 3),
            }
        )

    return {
        "seed_id": seed_id,
        "name": name,
        "therapeutic_class": tclass,
        "smiles": smiles,
        "n_analogs": len(rows),
        "analog_rows": rows,
        "runtime_s": time.perf_counter() - t0,
    }


# ───── Aggregation ─────


def aggregate(per_seed_results: list[dict]) -> dict:
    """Compute headline metrics under two filter conditions."""
    all_rows: list[dict] = []
    for r in per_seed_results:
        for ar in r.get("analog_rows", []):
            ar["therapeutic_class"] = r["therapeutic_class"]
            all_rows.append(ar)

    # Condition A: default (Murcko gate ON = scaffold_preserved=True)
    default = [r for r in all_rows if r["scaffold_preserved"]]
    # Condition B: ablation (Murcko gate OFF = all analogs)
    ablation = all_rows

    def pct(num, denom):
        return round(100 * num / denom, 2) if denom else 0.0

    def cond_summary(label, rows):
        n = len(rows)
        if n == 0:
            return {"condition": label, "n_analogs": 0}
        return {
            "condition": label,
            "n_analogs": n,
            "pct_scaffold_preserved": pct(sum(1 for r in rows if r["scaffold_preserved"]), n),
            "pct_pains_alert": pct(sum(1 for r in rows if r["has_pains"]), n),
            "pct_brenk_alert": pct(sum(1 for r in rows if r["has_brenk"]), n),
            "pct_clean": pct(sum(1 for r in rows if not r["has_pains"] and not r["has_brenk"]), n),
            "pct_lipinski_pass": pct(sum(1 for r in rows if r["lipinski_violations"] <= 1), n),
            "mean_heavy_atom_delta": round(sum(r["heavy_atom_delta"] for r in rows) / n, 3),
            "mean_logp_delta": round(sum(r["logp_delta"] for r in rows) / n, 3),
        }

    summary = {
        "n_seeds": len(per_seed_results),
        "n_seeds_with_analogs": sum(1 for r in per_seed_results if r.get("n_analogs", 0) > 0),
        "mean_analogs_per_seed": round(
            sum(r.get("n_analogs", 0) for r in per_seed_results) / max(1, len(per_seed_results)), 1
        ),
        "median_analogs_per_seed": sorted(r.get("n_analogs", 0) for r in per_seed_results)[
            len(per_seed_results) // 2
        ],
        "conditions": {
            "default_murcko_gate_on": cond_summary("default", default),
            "ablation_murcko_gate_off": cond_summary("ablation", ablation),
        },
    }

    # Per-class break-out (default condition only)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in default:
        by_class[r["therapeutic_class"]].append(r)
    summary["per_class_default"] = {
        cls: cond_summary(f"default::{cls}", rows) for cls, rows in by_class.items()
    }
    return summary


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(seed_path: Path) -> dict:
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), text=True
        ).strip()
    except Exception:
        git_sha = "unknown"
    import rdkit

    smirks_path = REPO / "backend/app/services/lead_optimizer/smirks_library.py"
    return {
        "git_sha": git_sha,
        "rdkit_version": rdkit.__version__,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "smirks_library_sha256": file_sha256(smirks_path),
        "smirks_library_entry_count": len(SMIRKS_LIBRARY),
        "seed_input": str(seed_path),
        "seed_input_sha256": file_sha256(seed_path),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with open(args.seeds, newline="") as f:
        seeds = list(csv.DictReader(f))

    print(f"[exp2] loaded {len(seeds)} seeds; SMIRKS={len(SMIRKS_LIBRARY)}; workers={args.workers}",
          file=sys.stderr)

    t0 = time.perf_counter()
    if args.workers > 1:
        with mp.Pool(args.workers) as pool:
            per_seed = pool.map(evaluate_seed, seeds)
    else:
        per_seed = [evaluate_seed(s) for s in seeds]
    total = time.perf_counter() - t0
    print(f"[exp2] runtime: {total:.1f}s ({total/len(seeds):.2f}s/seed)", file=sys.stderr)

    # Per-analog CSV
    out_rows = args.output / "per_analog.csv"
    with open(out_rows, "w", newline="") as f:
        cols = [
            "seed_id",
            "therapeutic_class",
            "analog_smiles",
            "scaffold_preserved",
            "has_pains",
            "has_brenk",
            "lipinski_violations",
            "heavy_atom_delta",
            "logp_delta",
            "n_smirks_producing_it",
        ]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in per_seed:
            for ar in r.get("analog_rows", []):
                ar["therapeutic_class"] = r["therapeutic_class"]
                w.writerow(ar)

    # Per-seed summary CSV
    out_seed = args.output / "per_seed.csv"
    with open(out_seed, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed_id", "name", "therapeutic_class", "n_analogs", "error", "runtime_s"])
        for r in per_seed:
            w.writerow(
                [
                    r["seed_id"],
                    r["name"],
                    r.get("therapeutic_class", ""),
                    r.get("n_analogs", 0),
                    r.get("error", ""),
                    round(r.get("runtime_s", 0), 3),
                ]
            )

    # Summary JSON
    summary = aggregate(per_seed)
    summary["total_runtime_s"] = round(total, 2)
    with open(args.output / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Manifest
    with open(args.output / "manifest.json", "w") as f:
        json.dump(manifest(args.seeds), f, indent=2)

    print()
    print("=" * 70)
    print(f"  Seeds:                {summary['n_seeds']}")
    print(f"  Seeds with analogs:   {summary['n_seeds_with_analogs']}")
    print(f"  Mean analogs/seed:    {summary['mean_analogs_per_seed']}")
    print(f"  Median analogs/seed:  {summary['median_analogs_per_seed']}")
    print()
    for k, v in summary["conditions"].items():
        print(f"  [{k}]")
        for kk, vv in v.items():
            print(f"    {kk:30s} {vv}")
    print("=" * 70)


if __name__ == "__main__":
    main()
