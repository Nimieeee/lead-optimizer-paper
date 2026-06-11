#!/usr/bin/env python3
"""Parse frontend/src/constants/drugPool.ts -> seed_leads.csv for Exp 2."""

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
POOL = REPO / "frontend/src/constants/drugPool.ts"
OUT = HERE / "data" / "seed_leads.csv"

content = POOL.read_text()
entries = re.findall(
    r"\{\s*name:\s*['\"]([^'\"]+)['\"]"
    r",\s*smiles:\s*['\"]([^'\"]+)['\"]"
    r"(?:,\s*year:\s*(\d+))?"
    r"\s*,\s*class:\s*['\"]([^'\"]+)['\"]",
    content,
)

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["seed_id", "name", "smiles", "approval_year", "therapeutic_class"])
    for i, (name, smi, year, cls) in enumerate(entries, start=1):
        w.writerow([f"SEED_{i:03d}", name, smi, year or "", cls])

print(f"[seeds] wrote {len(entries)} entries -> {OUT}", file=sys.stderr)
