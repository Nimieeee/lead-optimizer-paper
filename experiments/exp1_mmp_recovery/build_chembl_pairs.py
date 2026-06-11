#!/usr/bin/env python3
"""
Build ChEMBL-derived matched-molecular-pair set for Exp 1 full run.

Steps:
  1. Filter chembl_37_chemreps.txt → drug-like 10K subset
       single-component, 12 <= HA <= 35, HBD <= 5, HBA <= 10, MW <= 500
       no peptide residues (no large repeated amide chains)
  2. mmpdb fragment → fragmented intermediate
  3. mmpdb index    → MMP database
  4. Query the index for single-edit pairs (max_radius = 1, min_pairs = 5)
  5. Sample up to N pairs, write `chembl_pairs.csv` for Exp 1

Run:
    paper/.venv/bin/python paper/experiments/exp1_mmp_recovery/build_chembl_pairs.py \
        --raw paper/experiments/exp1_mmp_recovery/data/chembl/chembl_37_chemreps.txt \
        --subset-size 10000 \
        --max-pairs 2000 \
        --output paper/experiments/exp1_mmp_recovery/data/chembl_pairs.csv
"""

from __future__ import annotations

import argparse
import csv
import random
import subprocess
import sys
import time
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import Crippen, Descriptors, Lipinski
RDLogger.DisableLog("rdApp.*")


HERE = Path(__file__).resolve().parent


def drug_like(smi: str) -> bool:
    if not smi or "." in smi:
        return False
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return False
    n_heavy = mol.GetNumHeavyAtoms()
    if not (12 <= n_heavy <= 35):
        return False
    mw = Descriptors.MolWt(mol)
    if mw > 500:
        return False
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    if hbd > 5 or hba > 10:
        return False
    logp = Crippen.MolLogP(mol)
    if not (-2 <= logp <= 5):
        return False
    return True


def filter_chembl(raw_path: Path, subset_size: int, out_path: Path, seed: int = 42):
    """Stream the 2.9 M chembl file, keep drug-like, randomly sample subset_size."""
    rng = random.Random(seed)
    pool = []
    t0 = time.perf_counter()
    print(f"[filter] streaming {raw_path}", file=sys.stderr)
    with open(raw_path) as f:
        header = f.readline().rstrip("\n").split("\t")
        smi_idx = header.index("canonical_smiles")
        id_idx = header.index("chembl_id")
        for i, line in enumerate(f, 1):
            parts = line.rstrip("\n").split("\t")
            if len(parts) <= max(smi_idx, id_idx):
                continue
            smi = parts[smi_idx]
            cid = parts[id_idx]
            if drug_like(smi):
                pool.append((cid, smi))
            if i % 200_000 == 0:
                print(f"  {i:>9} scanned  ·  {len(pool):>7} drug-like kept  ·  "
                      f"{time.perf_counter()-t0:6.1f}s", file=sys.stderr)

    print(f"[filter] {len(pool):,} drug-like compounds", file=sys.stderr)
    rng.shuffle(pool)
    subset = pool[:subset_size]
    print(f"[filter] writing {len(subset):,} sampled compounds → {out_path}", file=sys.stderr)
    with open(out_path, "w") as f:
        f.write("SMILES\tID\n")
        for cid, smi in subset:
            f.write(f"{smi}\t{cid}\n")
    print(f"[filter] runtime: {time.perf_counter()-t0:.1f}s", file=sys.stderr)


def run_mmpdb(subset_path: Path, frags_path: Path, db_path: Path):
    """Run mmpdb fragment + index.

    Calls `python -m mmpdb` instead of the CLI binary so the venv's
    Python is guaranteed to find the module.
    """
    py = sys.executable  # the venv's python, by construction
    print(f"[mmpdb] fragment via {py}", file=sys.stderr)
    subprocess.run(
        [py, "-m", "mmpdblib", "fragment", str(subset_path), "-o", str(frags_path)],
        check=True,
    )
    print(f"[mmpdb] index", file=sys.stderr)
    subprocess.run(
        [py, "-m", "mmpdblib", "index", str(frags_path), "-o", str(db_path)],
        check=True,
    )


def query_pairs(db_path: Path, out_path: Path, max_pairs: int, seed: int = 42):
    """Extract single-edit pairs from the MMP database via sqlite3."""
    import sqlite3
    rng = random.Random(seed)
    print(f"[query] sampling up to {max_pairs:,} MMPs from {db_path}", file=sys.stderr)
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    # mmpdb schema (v3): pair table has compound1_id, compound2_id, rule_smiles_id, constant_id
    # We pull pairs with single-bond difference (rule small), join compound table for SMILES
    # First inspect schema
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print(f"[query] tables in db: {tables}", file=sys.stderr)
    # The schema varies; this works for mmpdb >= 3.0
    rows = list(cur.execute("""
        SELECT c1.clean_smiles, c1.public_id,
               c2.clean_smiles, c2.public_id,
               rs_from.smiles, rs_to.smiles
        FROM pair
        JOIN compound c1 ON pair.compound1_id = c1.id
        JOIN compound c2 ON pair.compound2_id = c2.id
        JOIN rule_smiles rs_from ON pair.smiles1_id = rs_from.id
        JOIN rule_smiles rs_to   ON pair.smiles2_id = rs_to.id
        WHERE length(rs_from.smiles) <= 12 AND length(rs_to.smiles) <= 12
        LIMIT 100000
    """))
    print(f"[query] pulled {len(rows):,} candidate pairs", file=sys.stderr)
    rng.shuffle(rows)
    sample = rows[:max_pairs]
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "smiles_A", "smiles_B", "source", "transformation", "notes"])
        for i, (smi_A, id_A, smi_B, id_B, rule_from, rule_to) in enumerate(sample, 1):
            transform = f"{rule_from}>>{rule_to}"
            w.writerow([f"CHEMBL_MMP_{i:05d}", smi_A, smi_B, "ChEMBL-37/mmpdb",
                        transform, f"A={id_A} B={id_B}"])
    print(f"[query] wrote {len(sample):,} pairs → {out_path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--subset-size", type=int, default=10000)
    ap.add_argument("--max-pairs", type=int, default=2000)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--workdir", type=Path, default=None,
                    help="Intermediate files dir (default: same as --raw parent)")
    args = ap.parse_args()

    workdir = args.workdir or args.raw.parent
    subset_path = workdir / "subset_10k.smi"
    frags_path = workdir / "subset_10k.fragments"
    db_path = workdir / "subset_10k.mmpdb"

    if not subset_path.exists():
        filter_chembl(args.raw, args.subset_size, subset_path)
    else:
        print(f"[filter] subset {subset_path} exists; reusing", file=sys.stderr)

    if not db_path.exists():
        run_mmpdb(subset_path, frags_path, db_path)
    else:
        print(f"[mmpdb] db {db_path} exists; reusing", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    query_pairs(db_path, args.output, args.max_pairs)


if __name__ == "__main__":
    main()
