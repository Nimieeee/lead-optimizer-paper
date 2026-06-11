#!/usr/bin/env python3
"""
Experiment 4, End-to-end case study.

For each lead in data/cases.csv, run the full 12-stage lead-optimization
pipeline (no LID; all functional groups become TARGET) and capture
stage-by-stage attrition + top-10 analogs.

Must run on the VPS (or a host with backend deps installed). Driver imports
backend.app.services.lead_optimizer.orchestrator.run_lead_optimization
directly, bypasses HTTP entirely, so no auth needed.

Use:
    python3 paper/experiments/exp4_case_study/run_on_vps.py \\
        --cases paper/experiments/exp4_case_study/data/cases.csv \\
        --output paper/experiments/exp4_case_study/results
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
# REPO is only used to look up git SHA for the manifest; tolerate
# alternate layouts (VPS deploys the file standalone under /tmp).
try:
    REPO = HERE.parents[2]
except IndexError:
    REPO = HERE

# On VPS: backend is at /var/www/benchside-backend/backend.
# Locally for verification: backend lives in the repo at <repo>/backend.
for candidate in (
    REPO / "backend",
    Path("/var/www/benchside-backend/backend"),
    HERE,  # fall-through; will fail loudly below if backend not found
):
    if (candidate / "app" / "services" / "lead_optimizer" / "orchestrator.py").exists():
        sys.path.insert(0, str(candidate))
        break

from app.services.lead_optimizer.orchestrator import run_lead_optimization  # noqa: E402
from app.core.database import init_db, db as db_manager  # noqa: E402
from app.core.container import container  # noqa: E402


async def init_container():
    """Mimic main.py:lifespan() startup sequence so ServiceContainer is ready."""
    await init_db()
    container.initialize(db_manager.get_client())
    return True


PROGRESS_EVENTS: list[dict] = []


async def progress_callback(stage: str, pct: int, message: str):
    PROGRESS_EVENTS.append({"stage": stage, "pct": pct, "message": message, "t": time.perf_counter()})


def _flatten_result(case_id: str, name: str, smiles: str, result, runtime_s: float) -> dict:
    """Convert OptimizationResult to a JSON-serialisable dict."""
    if result is None:
        return {"case_id": case_id, "name": name, "smiles": smiles, "error": "pipeline_returned_none", "runtime_s": runtime_s}
    top_analogs = []
    for a in result.top_analogs[:10]:
        top_analogs.append(
            {
                "smiles": a.smiles,
                "modifications": a.modifications,
                "pareto_rank": a.pareto_rank,
                "pareto_score": a.pareto_score,
                "sa_score": a.sa_score,
                "rationale_excerpt": (a.agent_rationale or "")[:200],
                "admet_summary": (
                    {k: a.admet_results.get(k) for k in list((a.admet_results or {}).keys())[:6]}
                    if a.admet_results
                    else None
                ),
            }
        )

    return {
        "case_id": case_id,
        "name": name,
        "lead_smiles": smiles,
        "runtime_s": round(runtime_s, 2),
        "lead_profile": {
            "smiles": result.lead_profile.smiles if result.lead_profile else smiles,
            "sa_score": getattr(result, "lead_sa_score", None),
            "syba_score": getattr(result, "lead_syba_score", None),
        },
        "pipeline_attrition": {
            "total_strategies_proposed": result.total_strategies,
            "total_analogs_generated": result.total_analogs_generated,
            "total_passed_prefilter": result.total_passed_prefilter,
            "total_passed_admet": result.total_passed_admet,
            "diversity_clusters_after_ranking": result.diversity_clusters,
        },
        "top_analogs_top10": top_analogs,
        "used_lid": result.used_lid,
        "search_space_size": result.search_space_size,
        "iterations_used": result.iterations_used,
        "errors": result.errors,
        "methodology_notes_excerpt": (result.methodology_notes or "")[:500],
        "report_pdf_path": result.report_pdf_path,
        "sdf_path": result.sdf_path,
    }


async def run_case(case: dict) -> dict:
    PROGRESS_EVENTS.clear()
    t0 = time.perf_counter()

    # Optional LID, if data/<lid_filename> exists, load it.
    lid_bytes = None
    lid_filename = (case.get("lid_filename") or "").strip()
    if lid_filename:
        candidate = HERE / "data" / lid_filename
        if candidate.exists():
            lid_bytes = candidate.read_bytes()

    try:
        result = await run_lead_optimization(
            lead_smiles=case["smiles"],
            lid_diagram=lid_bytes,
            user_context=case.get("notes", ""),
            target_analogs=500,
            progress_callback=progress_callback,
            task_id=None,
            vision_output=None,
        )
        runtime = time.perf_counter() - t0
        out = _flatten_result(case["case_id"], case["name"], case["smiles"], result, runtime)
        out["progress_events_count"] = len(PROGRESS_EVENTS)
        out["progress_events_excerpt"] = PROGRESS_EVENTS[:5] + ["..."] + PROGRESS_EVENTS[-5:] if len(PROGRESS_EVENTS) > 10 else PROGRESS_EVENTS
        return out
    except Exception:
        return {
            "case_id": case["case_id"],
            "name": case["name"],
            "smiles": case["smiles"],
            "error": "exception",
            "traceback": traceback.format_exc(),
            "runtime_s": round(time.perf_counter() - t0, 2),
        }


async def main_async(cases_path: Path, out_dir: Path):
    print("[exp4] initialising ServiceContainer (init_db + container.initialize)", file=sys.stderr)
    await init_container()
    print("[exp4] container ready", file=sys.stderr)

    with open(cases_path, newline="") as f:
        cases = list(csv.DictReader(f))
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[exp4] {len(cases)} cases", file=sys.stderr)
    summaries = []
    for c in cases:
        print(f"[exp4] running {c['case_id']} {c['name']}", file=sys.stderr)
        out = await run_case(c)
        summaries.append(out)
        case_out = out_dir / f"{c['case_id']}.json"
        with open(case_out, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"[exp4] wrote {case_out}", file=sys.stderr)

    with open(out_dir / "summary.json", "w") as f:
        json.dump({"n_cases": len(summaries), "cases": summaries}, f, indent=2, default=str)

    # Manifest
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO), text=True).strip()
    except Exception:
        git_sha = "unknown"
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(
            {
                "git_sha": git_sha,
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "cases_input": str(cases_path),
                "n_cases": len(cases),
                "host": os.uname().nodename,
            },
            f,
            indent=2,
        )

    print(f"[exp4] done; results in {out_dir}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    asyncio.run(main_async(args.cases, args.output))


if __name__ == "__main__":
    main()
