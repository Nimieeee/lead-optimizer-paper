#!/usr/bin/env python3
"""
Experiment 3, Vision Agent self-consistency on a fixed LID.

Question: Given one fixed LID image, how reproducible are the
Vision Agent's restricted vs target classifications across N runs?
This is a self-consistency metric (no gold standard required) that
measures real Vision Agent variance + the chemistry-validator drop rate.

For each of N runs we capture:
  - restricted_groups (set of labels with residues + interaction_types)
  - target_groups (set of labels)
  - validator_drops (chemistry-impossible classifications removed)
  - runtime
  - provider used (tier 1 / tier 2 / tier 3)

Aggregates: consensus restricted set (atoms appearing in >=K of N runs),
Jaccard similarity across pairs of runs, mean/std of validator drops.

Must run on the VPS so the production vision-agent provider chain is
available.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    REPO = HERE.parents[2]
except IndexError:
    REPO = HERE

for candidate in (
    REPO / "backend",
    Path("/var/www/benchside-backend/backend"),
    HERE,
):
    if (candidate / "app" / "services" / "lead_optimizer" / "agents" / "vision_agent.py").exists():
        sys.path.insert(0, str(candidate))
        break

from app.services.lead_optimizer.agents.vision_agent import run_vision_agent  # noqa: E402
from app.services.lead_optimizer.rdkit_engine import pre_scan_molecule  # noqa: E402


class CountingHandler(logging.Handler):
    """Capture chemistry-validator + hallucination drop warnings per run."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.drops_hallucinated = 0
        self.drops_chem_invalid = 0
        self.records = []

    def emit(self, record):
        msg = record.getMessage()
        if "dropping hallucinated" in msg:
            self.drops_hallucinated += 1
        if "dropping chemically invalid" in msg:
            self.drops_chem_invalid += 1
        self.records.append(msg)

    def reset(self):
        self.drops_hallucinated = 0
        self.drops_chem_invalid = 0
        self.records = []


def _serialise_output(vo) -> dict:
    return {
        "restricted_groups": [
            {
                "group_name": g.group_name,
                "residue": getattr(g, "residue", ""),
                "residues": list(getattr(g, "residues", []) or []),
                "interaction_type": (g.interaction_type.value if hasattr(g, "interaction_type") and hasattr(g.interaction_type, "value") else str(getattr(g, "interaction_type", ""))),
                "interaction_types": [
                    (t.value if hasattr(t, "value") else str(t))
                    for t in (getattr(g, "interaction_types", []) or [])
                ],
                "atom_indices": list(getattr(g, "atom_indices", []) or []),
            }
            for g in (vo.restricted_groups or [])
        ],
        "target_groups": [
            {
                "group_name": g.group_name,
                "position_description": getattr(g, "position_description", ""),
                "atom_indices": list(getattr(g, "atom_indices", []) or []),
            }
            for g in (vo.target_groups or [])
        ],
        "scaffold_atoms": list(getattr(vo, "scaffold_atoms", []) or []),
        "provider": getattr(vo, "used_provider", "unknown"),
    }


async def run_one(lead_smiles: str, diagram_bytes: bytes, scan: dict, run_idx: int, handler: CountingHandler) -> dict:
    handler.reset()
    t0 = time.perf_counter()
    try:
        vo = await run_vision_agent(
            lead_smiles=lead_smiles,
            diagram_bytes=diagram_bytes,
            detected_groups=scan["all"],
            labeled_instances=scan.get("labeled", []),
        )
        runtime = time.perf_counter() - t0
        return {
            "run_idx": run_idx,
            "ok": True,
            "runtime_s": round(runtime, 2),
            "drops_hallucinated": handler.drops_hallucinated,
            "drops_chem_invalid": handler.drops_chem_invalid,
            "output": _serialise_output(vo),
        }
    except Exception as e:
        return {
            "run_idx": run_idx,
            "ok": False,
            "runtime_s": round(time.perf_counter() - t0, 2),
            "drops_hallucinated": handler.drops_hallucinated,
            "drops_chem_invalid": handler.drops_chem_invalid,
            "error": repr(e),
        }


def aggregate(runs: list[dict]) -> dict:
    ok_runs = [r for r in runs if r["ok"]]
    n_ok = len(ok_runs)

    # Restricted atom-set consensus (use atom_indices when present, fallback to (group_name, sorted residues))
    def key_set(run):
        keys = set()
        for g in run["output"]["restricted_groups"]:
            if g.get("atom_indices"):
                for a in g["atom_indices"]:
                    keys.add(("atom", a))
            else:
                residues = g.get("residues") or ([g["residue"]] if g.get("residue") else [])
                keys.add(("name", g["group_name"], tuple(sorted(residues))))
        return keys

    sets = [key_set(r) for r in ok_runs]

    # Jaccard pairwise
    jaccards = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            inter = len(sets[i] & sets[j])
            union = len(sets[i] | sets[j])
            jaccards.append(inter / union if union else 1.0)

    # Consensus: keys appearing in >= K of N runs, for various K
    key_counter: Counter = Counter()
    for s in sets:
        for k in s:
            key_counter[k] += 1
    consensus = {
        k_threshold: [str(k) for k, c in key_counter.items() if c >= k_threshold]
        for k_threshold in (
            n_ok,                 # appears in all
            max(1, int(n_ok * 0.8)),  # appears in >=80%
            max(1, int(n_ok * 0.6)),  # appears in >=60%
            max(1, int(n_ok * 0.5)),  # majority
        )
    }

    # Provider usage
    providers = Counter(r["output"]["provider"] for r in ok_runs)

    drops_h = [r["drops_hallucinated"] for r in ok_runs]
    drops_c = [r["drops_chem_invalid"] for r in ok_runs]

    def stat(xs):
        if not xs:
            return {"n": 0}
        mean = sum(xs) / len(xs)
        return {
            "n": len(xs),
            "mean": round(mean, 3),
            "min": min(xs),
            "max": max(xs),
            "std": round((sum((x - mean) ** 2 for x in xs) / len(xs)) ** 0.5, 3),
        }

    return {
        "n_runs_total": len(runs),
        "n_runs_ok": n_ok,
        "mean_jaccard_pairwise": round(sum(jaccards) / len(jaccards), 3) if jaccards else None,
        "min_jaccard_pairwise": round(min(jaccards), 3) if jaccards else None,
        "max_jaccard_pairwise": round(max(jaccards), 3) if jaccards else None,
        "consensus_keys_present_in_all": len(consensus[n_ok]) if n_ok else 0,
        "consensus_keys_present_in_80pct": len(consensus[max(1, int(n_ok * 0.8))]),
        "consensus_keys_present_in_60pct": len(consensus[max(1, int(n_ok * 0.6))]),
        "consensus_keys_present_in_majority": len(consensus[max(1, int(n_ok * 0.5))]),
        "drops_hallucinated_stat": stat(drops_h),
        "drops_chem_invalid_stat": stat(drops_c),
        "drops_any_per_run": stat([h + c for h, c in zip(drops_h, drops_c)]),
        "provider_usage": dict(providers),
        "runtime_stat": stat([r["runtime_s"] for r in ok_runs]),
    }


async def main_async(lid_path: Path, lead_smiles: str, n_runs: int, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read image bytes
    diagram_bytes = lid_path.read_bytes()
    print(f"[exp3] LID file: {lid_path}  ({len(diagram_bytes):,} bytes)", file=sys.stderr)

    # Pre-scan once (deterministic; same input -> same labelled set)
    scan = pre_scan_molecule(lead_smiles)
    print(f"[exp3] pre-scan: {len(scan['all'])} groups, {len(scan.get('labeled', []))} labelled, "
          f"{len(scan.get('scaffold_atoms', set()))} scaffold atoms",
          file=sys.stderr)

    # Wire up a log handler so we can count validator drops per run
    target_logger = logging.getLogger("app.services.lead_optimizer.agents.vision_agent")
    target_logger.setLevel(logging.WARNING)
    handler = CountingHandler()
    target_logger.addHandler(handler)

    runs = []
    for i in range(n_runs):
        print(f"[exp3] run {i+1}/{n_runs}", file=sys.stderr)
        r = await run_one(lead_smiles, diagram_bytes, scan, i, handler)
        runs.append(r)
        with open(out_dir / f"run_{i:02d}.json", "w") as f:
            json.dump(r, f, indent=2)

    summary = aggregate(runs)
    summary["lid_path"] = str(lid_path)
    summary["lead_smiles"] = lead_smiles
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print()
    print("=" * 60)
    print(f"  Runs:                 {summary['n_runs_total']} ({summary['n_runs_ok']} OK)")
    print(f"  Pairwise Jaccard:     mean={summary['mean_jaccard_pairwise']}  "
          f"[{summary['min_jaccard_pairwise']}, {summary['max_jaccard_pairwise']}]")
    print(f"  Restricted keys consensus:")
    print(f"    in all runs:         {summary['consensus_keys_present_in_all']}")
    print(f"    in >=80% of runs:    {summary['consensus_keys_present_in_80pct']}")
    print(f"    in >=60% of runs:    {summary['consensus_keys_present_in_60pct']}")
    drops_any = summary["drops_any_per_run"].get("mean", "n/a")
    drops_h = summary["drops_hallucinated_stat"].get("mean", "n/a")
    drops_c = summary["drops_chem_invalid_stat"].get("mean", "n/a")
    rt_mean = summary["runtime_stat"].get("mean", "n/a")
    print(f"  Validator drops/run:  any={drops_any}  hallucinated={drops_h}  chem-invalid={drops_c}")
    print(f"  Provider usage:       {summary['provider_usage']}")
    print(f"  Runtime/run:          mean={rt_mean}s")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lid", required=True, type=Path, help="Path to LID PNG")
    ap.add_argument("--smiles", required=True, help="Lead SMILES corresponding to the LID")
    ap.add_argument("--n-runs", type=int, default=8)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    asyncio.run(main_async(args.lid, args.smiles, args.n_runs, args.output))


if __name__ == "__main__":
    main()
