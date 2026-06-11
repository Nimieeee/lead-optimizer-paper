#!/usr/bin/env python3
"""
Cross-provider, cross-model benchmark for Lead Optimizer stages 2, 5, 6.

Stages:
  stage2_vision       , Vision Agent on a fixed LID, N=8 reps per model.
                         14 vision models. Metrics: self-consistency Jaccard,
                         JSON validity, mean restricted-group count, runtime.
  stage5_context      , Project-context analysis on 4 contexts, 3 reps.
                         11 text models. Metrics: JSON validity,
                         endpoint-priority rubric score, runtime.
  stage6_optimization , Optimization-agent SAR strategy proposal on 4 leads, 3 reps.
                         11 text models. Metrics: JSON validity, strategy count,
                         strategy-maps-to-real-SMIRKS-category rate, runtime.

All prompts reused verbatim from the production code (no drift).

Usage on the VPS (after OPENAI_API_KEY + GEMINI_API_KEY are in /home/ubuntu/.env):
    set -a; source /home/ubuntu/.env; set +a
    cd /tmp/exp5_model_benchmark
    PYTHONPATH=/var/www/benchside-backend/backend \
        python3 run_benchmark.py --stage stage2_vision  --output results/
    python3 run_benchmark.py --stage stage5_context     --output results/
    python3 run_benchmark.py --stage stage6_optimization --output results/
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# VPS path injection for production prompts/schemas
_candidates = [Path("/var/www/benchside-backend/backend")]
try:
    _candidates.append(HERE.parents[2] / "backend")
except IndexError:
    pass
for candidate in _candidates:
    if (candidate / "app" / "services" / "lead_optimizer" / "prompts.py").exists():
        sys.path.insert(0, str(candidate))
        break

from providers import call, ProviderResponse  # noqa: E402

# Production prompts + schemas
from app.services.lead_optimizer.prompts import (   # noqa: E402
    VISION_AGENT_SYSTEM_PROMPT,
    OPTIMIZATION_AGENT_SYSTEM_PROMPT,
)
from app.services.lead_optimizer.context_analyzer import CONTEXT_ANALYZER_PROMPT  # noqa: E402
from app.services.lead_optimizer.rdkit_engine import pre_scan_molecule  # noqa: E402


# ──────────────────────────────────────────────────────────────
# JSON extraction (the production parser tolerates fences + prose)


def extract_json(text: str) -> Optional[dict]:
    """Strip code fences, find first { then matching }, json.loads."""
    if not text:
        return None
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```", "", text)
    start = text.find("{")
    if start == -1:
        return None
    # Scan for matching brace, tracking strings + escapes
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    return None
    return None


# ──────────────────────────────────────────────────────────────
# Stage 2, vision benchmark


def jaccard(a: set, b: set) -> float:
    u = a | b
    return (len(a & b) / len(u)) if u else 1.0


def restricted_atom_key_set(parsed: dict) -> set:
    """Collapse restricted_groups into a key set for cross-rep comparison."""
    keys = set()
    for g in (parsed or {}).get("restricted_groups", []) or []:
        ai = g.get("atom_indices") or []
        if ai:
            for a in ai:
                keys.add(("atom", a))
        else:
            name = g.get("group_name", "")
            res = sorted(g.get("residues") or ([g["residue"]] if g.get("residue") else []))
            keys.add(("name", name, tuple(res)))
    return keys


async def run_stage2(models: list, output_dir: Path, lid_path: Path, smiles: str, n_reps: int):
    diagram_bytes = lid_path.read_bytes()
    image_b64 = base64.b64encode(diagram_bytes).decode("ascii")

    # Reproduce the prompt the production agent builds: it injects
    # detected_groups + visual_hints, so we replicate that exactly.
    scan = pre_scan_molecule(smiles)
    detected_str = "\n".join(f"- {g}" for g in scan["all"]) or "(none detected)"
    user_msg = (
        f"Lead SMILES: {smiles}\n\n"
        f"SUBSTRUCTURE ANALYSIS:\n{detected_str}\n\n"
        f"Classify each functional group as RESTRICTED or TARGET. "
        f"Return strict JSON matching the schema described in the system prompt."
    )

    out_rows = []
    for m in models:
        provider, model = m["provider"], m["model"]
        print(f"  [stage2] {provider}/{model}  N={n_reps} reps ...", file=sys.stderr)
        runs = []
        for r in range(n_reps):
            resp = await call(provider, model, VISION_AGENT_SYSTEM_PROMPT, user_msg,
                              image_b64=image_b64, max_tokens=4096, timeout=120)
            parsed = extract_json(resp.text)
            keys = restricted_atom_key_set(parsed) if parsed else set()
            runs.append({
                "rep": r, "ok": resp.ok(),
                "json_valid": parsed is not None,
                "runtime_s": round(resp.runtime_s, 2),
                "usage_in": resp.usage_in, "usage_out": resp.usage_out,
                "error": resp.error,
                "n_restricted": len((parsed or {}).get("restricted_groups", []) or []),
                "n_target": len((parsed or {}).get("target_groups", []) or []),
                "key_set": list(map(list, keys)),
            })

        # Self-consistency Jaccard across reps
        sets = [set(map(tuple, [tuple(k) for k in run["key_set"]])) for run in runs if run["json_valid"]]
        jacc = []
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                jacc.append(jaccard(sets[i], sets[j]))

        out_rows.append({
            "provider": provider, "model": model,
            "n_reps": n_reps,
            "n_ok": sum(1 for r in runs if r["ok"]),
            "n_json_valid": sum(1 for r in runs if r["json_valid"]),
            "json_validity_rate": round(sum(1 for r in runs if r["json_valid"]) / n_reps, 3),
            "mean_jaccard_self": round(sum(jacc) / len(jacc), 3) if jacc else None,
            "mean_restricted": round(sum(r["n_restricted"] for r in runs if r["json_valid"]) / max(1, sum(1 for r in runs if r["json_valid"])), 2),
            "mean_target":     round(sum(r["n_target"]     for r in runs if r["json_valid"]) / max(1, sum(1 for r in runs if r["json_valid"])), 2),
            "mean_runtime_s": round(sum(r["runtime_s"] for r in runs) / n_reps, 2),
            "total_usage_in": sum(r["usage_in"] for r in runs),
            "total_usage_out": sum(r["usage_out"] for r in runs),
            "errors": [r["error"] for r in runs if r["error"]],
            "runs": runs,
        })
        # Stream-write each model's row so a crash doesn't lose work
        (output_dir / f"stage2_{provider}_{model.replace('/', '_')}.json").write_text(json.dumps(out_rows[-1], indent=2))

    # When using --filter, merge into existing summary rather than replace.
    summary_path = output_dir / "stage2_summary.json"
    if summary_path.exists():
        existing = json.loads(summary_path.read_text())
        keep = [e for e in existing if not any((e["provider"] == n["provider"] and e["model"] == n["model"]) for n in out_rows)]
        out_rows = keep + out_rows
    summary_path.write_text(json.dumps(out_rows, indent=2))
    print(f"[stage2] summary has {len(out_rows)} model rows → {summary_path}", file=sys.stderr)


# ──────────────────────────────────────────────────────────────
# Stage 5, project-context analysis benchmark


def score_context_priorities(parsed: dict, expected: dict) -> dict:
    """Compare LLM-returned ContextAnalysis to the rubric."""
    if not parsed:
        return {"valid": False, "score": 0.0, "details": "parse-fail"}
    priorities = parsed.get("endpoint_priorities") or parsed.get("priorities") or []
    if isinstance(priorities, dict):
        # flat form: {"BBB_Martins": {"weight": 1.0, ...}}
        prios = {k: v.get("weight", 1.0) if isinstance(v, dict) else v for k, v in priorities.items()}
    elif isinstance(priorities, list):
        # list form: [{"endpoint": "BBB_Martins", "weight": ...}]
        prios = {p.get("endpoint", "") or p.get("name", ""): p.get("weight", 1.0) for p in priorities if isinstance(p, dict)}
    else:
        prios = {}

    hard_stops_field = parsed.get("hard_stops") or parsed.get("hard_stop_thresholds") or {}
    if isinstance(hard_stops_field, list):
        hard_stops = set()
        for hs in hard_stops_field:
            if isinstance(hs, dict):
                e = hs.get("endpoint", "") or hs.get("name", "")
                if e: hard_stops.add(e)
            elif isinstance(hs, str):
                hard_stops.add(hs)
    else:
        hard_stops = set(hard_stops_field.keys() if isinstance(hard_stops_field, dict) else [])

    # Score: 1 point per expected "high" priority endpoint that ranks in top-3 by weight
    # Plus 0.5 per expected hard_stop that's also flagged as hard_stop
    score = 0.0
    max_score = 0.0
    details = {}

    top_endpoints = sorted(prios.items(), key=lambda x: -float(x[1] or 0))[:5]
    top_names = {e for e, _ in top_endpoints}

    for ep in expected.get("high", []):
        max_score += 1
        if ep in top_names:
            score += 1
            details[ep] = "found in top-5"
        else:
            details[ep] = "MISSING"

    for ep in expected.get("hard_stops", []):
        max_score += 0.5
        if ep in hard_stops:
            score += 0.5
            details["hardstop_" + ep] = "flagged"
        else:
            details["hardstop_" + ep] = "missing"

    return {
        "valid": True,
        "score": round(score, 2),
        "max_score": round(max_score, 2),
        "normalized": round(score / max_score, 3) if max_score else 0.0,
        "n_priorities_returned": len(prios),
        "details": details,
    }


async def run_stage5(models: list, output_dir: Path, contexts_path: Path, n_reps: int):
    contexts = json.loads(contexts_path.read_text())
    out_rows = []
    for m in models:
        provider, model = m["provider"], m["model"]
        print(f"  [stage5] {provider}/{model}  {len(contexts)} contexts × {n_reps} reps", file=sys.stderr)
        per_context = []
        for ctx in contexts:
            user_msg = (
                f"Project context:\n{ctx['context']}\n\n"
                f"Return a strict JSON ContextAnalysis with endpoint_priorities, "
                f"hard_stop_thresholds, and a primary_optimization_goal. Use the "
                f"endpoint names from the system prompt's known list."
            )
            rep_scores = []
            for r in range(n_reps):
                resp = await call(provider, model, CONTEXT_ANALYZER_PROMPT, user_msg,
                                  max_tokens=2048, timeout=60)
                parsed = extract_json(resp.text)
                rubric = score_context_priorities(parsed, ctx["expected_priorities"])
                rep_scores.append({
                    "rep": r, "ok": resp.ok(),
                    "json_valid": parsed is not None,
                    "runtime_s": round(resp.runtime_s, 2),
                    "usage_in": resp.usage_in, "usage_out": resp.usage_out,
                    "rubric": rubric,
                    "error": resp.error,
                })
            per_context.append({
                "context_id": ctx["id"], "context_label": ctx["label"],
                "n_reps": n_reps,
                "rubric_mean": round(sum(s["rubric"]["normalized"] for s in rep_scores if s["json_valid"]) / max(1, sum(1 for s in rep_scores if s["json_valid"])), 3),
                "json_valid_count": sum(1 for s in rep_scores if s["json_valid"]),
                "reps": rep_scores,
            })

        out_rows.append({
            "provider": provider, "model": model,
            "n_contexts": len(contexts), "n_reps": n_reps,
            "mean_rubric_score": round(sum(c["rubric_mean"] for c in per_context) / len(per_context), 3),
            "json_validity_rate": round(sum(c["json_valid_count"] for c in per_context) / (len(per_context) * n_reps), 3),
            "mean_runtime_s": round(sum(s["runtime_s"] for c in per_context for s in c["reps"]) / (len(per_context) * n_reps), 2),
            "total_usage_in": sum(s["usage_in"] for c in per_context for s in c["reps"]),
            "total_usage_out": sum(s["usage_out"] for c in per_context for s in c["reps"]),
            "per_context": per_context,
        })
        (output_dir / f"stage5_{provider}_{model.replace('/', '_')}.json").write_text(json.dumps(out_rows[-1], indent=2))

    summary_path = output_dir / "stage5_summary.json"
    if summary_path.exists():
        existing = json.loads(summary_path.read_text())
        keep = [e for e in existing if not any((e["provider"] == n["provider"] and e["model"] == n["model"]) for n in out_rows)]
        out_rows = keep + out_rows
    summary_path.write_text(json.dumps(out_rows, indent=2))
    print(f"[stage5] summary has {len(out_rows)} model rows → {summary_path}", file=sys.stderr)


# ──────────────────────────────────────────────────────────────
# Stage 6, optimization-agent benchmark


def score_optimization_output(parsed: dict, detected_groups: list, smirks_categories: set) -> dict:
    """Score: are strategies present, do they reference detected groups, do they map to real SMIRKS categories?"""
    if not parsed:
        return {"valid": False, "score": 0.0}
    strategies = parsed.get("strategies", []) or parsed.get("selected_strategies", []) or []
    if not isinstance(strategies, list):
        return {"valid": False, "score": 0.0, "details": "strategies-not-list"}

    n = len(strategies)
    detected_set = {g.lower() for g in detected_groups}

    refs_detected = 0
    cat_matches = 0
    for s in strategies:
        if not isinstance(s, dict): continue
        target = (s.get("target_group", "") or s.get("group", "") or "").lower()
        if target and any(d in target or target in d for d in detected_set):
            refs_detected += 1
        cat = (s.get("category", "") or s.get("smirks_category", "") or "").lower()
        if cat and any(c.lower() in cat or cat in c.lower() for c in smirks_categories):
            cat_matches += 1

    # Score: n_strategies (normalized to expected 8-12), references_real_groups, categories_match
    n_score = 1.0 if 6 <= n <= 14 else max(0.0, 1.0 - abs(n - 10) / 10.0)
    ref_score = refs_detected / n if n else 0.0
    cat_score = cat_matches / n if n else 0.0

    return {
        "valid": True,
        "n_strategies": n,
        "n_refs_detected": refs_detected,
        "n_cat_matches": cat_matches,
        "n_score": round(n_score, 3),
        "ref_score": round(ref_score, 3),
        "cat_score": round(cat_score, 3),
        "total": round((n_score + ref_score + cat_score) / 3, 3),
    }


async def run_stage6(models: list, output_dir: Path, leads_path: Path, n_reps: int):
    from app.services.lead_optimizer.smirks_library import SMIRKS_LIBRARY
    smirks_categories = {e.category for e in SMIRKS_LIBRARY.values()}

    leads = json.loads(leads_path.read_text())
    out_rows = []
    for m in models:
        provider, model = m["provider"], m["model"]
        print(f"  [stage6] {provider}/{model}  {len(leads)} leads × {n_reps} reps", file=sys.stderr)
        per_lead = []
        for lead in leads:
            scan = pre_scan_molecule(lead["smiles"])
            detected = scan["all"]
            user_msg = (
                f"Lead SMILES: {lead['smiles']}\n"
                f"Lead name: {lead['name']}\n"
                f"Target class: {lead['target_class']}\n\n"
                f"Detected functional groups (TARGET sites, these are editable):\n"
                + "\n".join(f"- {g}" for g in detected) + "\n\n"
                f"Project context: optimize for {lead['target_class']} indication.\n\n"
                f"Propose 8-12 ranked SAR strategies, each mapped to a SMIRKS-library category. "
                f"Return strict JSON per the schema in the system prompt."
            )
            rep_scores = []
            for r in range(n_reps):
                resp = await call(provider, model, OPTIMIZATION_AGENT_SYSTEM_PROMPT, user_msg,
                                  max_tokens=4096, timeout=120)
                parsed = extract_json(resp.text)
                rubric = score_optimization_output(parsed, detected, smirks_categories)
                rep_scores.append({
                    "rep": r, "ok": resp.ok(),
                    "json_valid": parsed is not None,
                    "runtime_s": round(resp.runtime_s, 2),
                    "usage_in": resp.usage_in, "usage_out": resp.usage_out,
                    "rubric": rubric,
                    "error": resp.error,
                })
            per_lead.append({
                "lead_id": lead["id"], "name": lead["name"],
                "n_reps": n_reps,
                "mean_total_score": round(sum(s["rubric"].get("total", 0) for s in rep_scores if s["json_valid"]) / max(1, sum(1 for s in rep_scores if s["json_valid"])), 3),
                "json_valid_count": sum(1 for s in rep_scores if s["json_valid"]),
                "reps": rep_scores,
            })

        out_rows.append({
            "provider": provider, "model": model,
            "n_leads": len(leads), "n_reps": n_reps,
            "mean_total_score": round(sum(l["mean_total_score"] for l in per_lead) / len(per_lead), 3),
            "json_validity_rate": round(sum(l["json_valid_count"] for l in per_lead) / (len(per_lead) * n_reps), 3),
            "mean_runtime_s": round(sum(s["runtime_s"] for l in per_lead for s in l["reps"]) / (len(per_lead) * n_reps), 2),
            "total_usage_in": sum(s["usage_in"] for l in per_lead for s in l["reps"]),
            "total_usage_out": sum(s["usage_out"] for l in per_lead for s in l["reps"]),
            "per_lead": per_lead,
        })
        (output_dir / f"stage6_{provider}_{model.replace('/', '_')}.json").write_text(json.dumps(out_rows[-1], indent=2))

    summary_path = output_dir / "stage6_summary.json"
    if summary_path.exists():
        existing = json.loads(summary_path.read_text())
        keep = [e for e in existing if not any((e["provider"] == n["provider"] and e["model"] == n["model"]) for n in out_rows)]
        out_rows = keep + out_rows
    summary_path.write_text(json.dumps(out_rows, indent=2))
    print(f"[stage6] summary has {len(out_rows)} model rows → {summary_path}", file=sys.stderr)


# ──────────────────────────────────────────────────────────────


async def main_async(args):
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    models_cfg = json.loads((HERE / "models.json").read_text())
    models = models_cfg[args.stage]

    if args.filter:
        wanted = {p.strip() for p in args.filter.split(",")}
        before = len(models)
        models = [m for m in models if f"{m['provider']}:{m['model']}" in wanted]
        print(f"[filter] {before} models → {len(models)} after filter ({sorted(wanted)})", file=sys.stderr)

    if args.stage == "stage2_vision":
        await run_stage2(
            models=models, output_dir=output_dir,
            lid_path=HERE / "data" / "dyrk1a_25014_LID.png",
            smiles="COc1ccc2c(c1)-c1cc(CO)ccc1C(C)(C)O2",
            n_reps=args.reps,
        )
    elif args.stage == "stage5_context":
        await run_stage5(
            models=models, output_dir=output_dir,
            contexts_path=HERE / "data" / "contexts.json",
            n_reps=args.reps,
        )
    elif args.stage == "stage6_optimization":
        await run_stage6(
            models=models, output_dir=output_dir,
            leads_path=HERE / "data" / "leads.json",
            n_reps=args.reps,
        )
    else:
        sys.exit(f"unknown stage {args.stage!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["stage2_vision", "stage5_context", "stage6_optimization"])
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--output", type=Path, default=HERE / "results")
    ap.add_argument("--filter", default=None,
                    help="Run only specified models. Comma-separated 'provider:model' pairs.")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
