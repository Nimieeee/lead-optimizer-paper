# Claims → Evidence Map

Every quantitative claim in `manuscript.md` is listed here with the exact
artefact (script, figure, table cell, or `summary.json` field) that supports
it. This document is the authoritative reproducibility index — when the
manuscript is updated, this file must be updated in the same commit.

A claim either points to (a) a results JSON field, (b) a figure rendered by a
specific script, or (c) a counted file. Anything else is a methodological
claim and is cross-referenced to the methods section.

---

## Pipeline architecture (§2)

| Claim | Evidence |
|---|---|
| 12 stages, fully wired | `backend/app/services/lead_optimizer/orchestrator.py:run_lead_optimization` |
| Per-instance SMARTS via 2D coords | `backend/app/services/lead_optimizer/rdkit_engine.py:_position_hint_from_2d`, `_label_instances` |
| Soft Murcko ring-topology gate | `backend/app/services/lead_optimizer/rdkit_engine.py:build_smarts_from_groups` |
| Chemistry-validity allowlists (6 tables) | `backend/app/services/lead_optimizer/chemistry_validator.py` |
| SMIRKS library: 479 entries / 22 categories / 100% validated | `paper/experiments/exp1_mmp_recovery/results/pilot/manifest.json:smirks_library_entry_count`; verified by `from app.services.lead_optimizer.smirks_library import SMIRKS_LIBRARY; len(SMIRKS_LIBRARY)` |
| SYBA is the primary synth-accessibility signal | `backend/app/services/lead_optimizer/ranking.py:_get_synth_difficulty`; `backend/app/services/gasa_service.py` (`synth_accessibility_service` fallback chain) |
| "Pareto-style penalty rank" is a sorted weighted scalar sum, not a real Pareto front | `backend/app/services/lead_optimizer/ranking.py:276-291` (declared explicitly in §5.2) |
| Upstream `admet_ai` (Chemprop v2) is the ADMET backbone | `backend/admet_engine.py` (`from admet_ai import ADMETModel`) |

## §4.1 — MMP recovery pilot (Figure 2)

| Claim | Value | Evidence |
|---|---|---|
**Pilot (corrected 2026-06-10):**
| 30 pairs evaluated | 30 | `paper/experiments/exp1_mmp_recovery/results/pilot/summary.json:n_pairs` |
| Exact recovery of B | **16/30 = 53.3 %** | `summary.json:n_B_recovered_exact` / `n_pairs`; `summary.json:any_recovery_rate` |
| Every recovered B lands at rank 1 | recall@1 = recall@500 = 53.3 % | `summary.json:recall_at_k` |
| 1 real library gap (indole→quinoline ring expansion); OMe→OCF3 prior gap was a data error | 1 | per-pair file; manuscript §4.1 audit-trail note |
| Median per-pair runtime | 0.19 s | `summary.json:median_runtime_s` |
| Mean unique analogs per pair | 74.5 | `summary.json:mean_unique_per_pair` |
| Mean best Tanimoto | 0.734 | `summary.json:mean_best_tanimoto` |
| Figure 2 rendered | — | `paper/figures/fig2_mmp_recovery.py` → `figures/out/fig2_mmp_recovery_pilot.{pdf,png}` |

**Unbiased ChEMBL-37 scale-up:**
| ChEMBL drug-like subset filtered (1.84 M → 2000 compounds for mmpdb) | 2000 | `paper/experiments/exp1_mmp_recovery/data/chembl/subset_2k.smi` |
| Raw mmpdb pairs | 41,310 | mmpdb DB `pair` table count |
| Sampled single-edit pairs (length(from)/length(to) ≤ 10) | 2856 candidate → **2000 evaluated** | `paper/experiments/exp1_mmp_recovery/data/chembl_pairs.csv` |
| Exact recovery of B (ChEMBL) | **310/2000 = 15.5 %** | `paper/experiments/exp1_mmp_recovery/results/chembl_2k/summary.json:any_recovery_rate` |
| Mean unique analogs per pair (ChEMBL) | 150.8 | `summary.json:mean_unique_per_pair` |
| Mean best Tanimoto (ChEMBL) | 0.755 | `summary.json:mean_best_tanimoto` |
| Top SMIRKS by recovery count (ChEMBL): META025 (119), RING_117 (42), OSUB_002 (37), AROM016 (34) | — | `summary.json:smirks_recovery_counts` |
| Runtime, 2000 pairs, 7 workers | 422 s = ~7 min | `summary.json:total_runtime_s` |

## §4.2 — Scaffold preservation + structural alerts (Figure 3)

| Claim | Value | Evidence |
|---|---|---|
| 129 marketed-drug seeds | 129 | `paper/experiments/exp2_scaffold_alerts/results/drugpool_129/summary.json:n_seeds` |
| Seeds with ≥1 analog | 119 | `summary.json:n_seeds_with_analogs` |
| Mean analogs/seed | 125.9 | `summary.json:mean_analogs_per_seed` |
| Total analogs, ablation (gate OFF) | 16,244 | `summary.json:conditions.ablation_murcko_gate_off.n_analogs` |
| Total analogs, default (gate ON) | 8,758 | `summary.json:conditions.default_murcko_gate_on.n_analogs` |
| Scaffold preservation, ablation | 53.92 % | `summary.json:conditions.ablation_murcko_gate_off.pct_scaffold_preserved` |
| Scaffold preservation, default | 100.0 % | `summary.json:conditions.default_murcko_gate_on.pct_scaffold_preserved` |
| PAINS rate, ablation | 9.47 % | `summary.json:conditions.ablation_murcko_gate_off.pct_pains_alert` |
| PAINS rate, default | 6.43 % | `summary.json:conditions.default_murcko_gate_on.pct_pains_alert` |
| Brenk rate, ablation | 44.29 % | `summary.json:conditions.ablation_murcko_gate_off.pct_brenk_alert` |
| Brenk rate, default | 46.47 % | `summary.json:conditions.default_murcko_gate_on.pct_brenk_alert` |
| Seed PAINS baseline | 5.0 % | inline computation in §4.2 narrative; reproducer in `paper/experiments/exp2_scaffold_alerts/run.py` baseline path |
| Seed Brenk baseline | 26.1 % | as above |
| Seed clean rate | 70.6 % | as above |
| Lipinski Ro5 pass, default | 96.08 % | `summary.json:conditions.default_murcko_gate_on.pct_lipinski_pass` |
| Mean ΔHA, default | +1.68 | `summary.json:conditions.default_murcko_gate_on.mean_heavy_atom_delta` |
| Mean ΔLogP, default | +0.06 | `summary.json:conditions.default_murcko_gate_on.mean_logp_delta` |
| Figure 3 rendered | — | `paper/figures/fig3_scaffold_alerts.py` → `figures/out/fig3_scaffold_alerts.{pdf,png}` |

## §4.3 — Vision Agent self-consistency (Figure 4)

| Claim | Value | Evidence |
|---|---|---|
| N = 8 runs on a fixed LID | 8 | `paper/experiments/exp3_vision_consistency/results/summary.json:n_runs_total` |
| Runs OK | 8/8 | `summary.json:n_runs_ok` |
| Pairwise Jaccard mean | 1.00 | `summary.json:mean_jaccard_pairwise` |
| Pairwise Jaccard range | [1.00, 1.00] | `summary.json:min_jaccard_pairwise`, `max_jaccard_pairwise` |
| Consensus restricted keys (in all runs) | 3 | `summary.json:consensus_keys_present_in_all` |
| Mean validator drops/run (hallucinated) | 0.0 | `summary.json:drops_hallucinated_stat.mean` |
| Mean validator drops/run (chem-invalid) | 0.0 | `summary.json:drops_chem_invalid_stat.mean` |
| Mean runtime/run | 5.06 s | `summary.json:runtime_stat.mean` |
| Runtime std dev | 0.56 s | `summary.json:runtime_stat.std` |
| Runtime range | [4.38 s, 6.28 s] | `summary.json:runtime_stat.min`, `runtime_stat.max` |
| Figure 4 rendered | — | `paper/figures/fig4_vision_consistency.py` → `figures/out/fig4_vision_consistency.{pdf,png}` |
| Caveat: temperature-zero perception | methodological | manuscript §4.3, §5.2 |

## §4.4 — End-to-end case study (Figure 5)

| Claim | Value | Evidence |
|---|---|---|
| 2 cases (DYRK1A + Linezolid) | 2 | `paper/experiments/exp4_case_study/results/summary.json:n_cases` |
| CASE_001 strategies proposed | 20 | `summary.json:cases[0].pipeline_attrition.total_strategies_proposed` |
| CASE_001 analogs generated | 149 | `cases[0].pipeline_attrition.total_analogs_generated` |
| CASE_001 after pre-filter | 62 | `cases[0].pipeline_attrition.total_passed_prefilter` |
| CASE_001 after ADMET | 62 | `cases[0].pipeline_attrition.total_passed_admet` |
| CASE_001 diversity clusters | 58 | `cases[0].pipeline_attrition.diversity_clusters_after_ranking` |
| CASE_001 runtime | 139.7 s | `cases[0].runtime_s` |
| CASE_001 rank-1 analog SMILES | `CC(C)(C)Oc1ccc2c(c1)-c1cc(CO)ccc1C(C)(C)O2` | `cases[0].top_analogs_top10[0].smiles` |
| CASE_001 rank-1 total-score | 0.586 | `cases[0].top_analogs_top10[0].pareto_score` |
| CASE_001 rank-1 SA score | 2.51 | `cases[0].top_analogs_top10[0].sa_score` |
| CASE_001 rank-1 MW | 312.4 | `cases[0].top_analogs_top10[0].admet_summary.molecular_weight` |
| CASE_001 rank-1 LogP | 4.65 | `cases[0].top_analogs_top10[0].admet_summary.logP` |
| CASE_001 rank-1 QED | 0.88 | `cases[0].top_analogs_top10[0].admet_summary.QED` |
| CASE_002 strategies proposed | 20 | `summary.json:cases[1].pipeline_attrition.total_strategies_proposed` |
| CASE_002 analogs generated | 71 | `cases[1].pipeline_attrition.total_analogs_generated` |
| CASE_002 after pre-filter | 24 | `cases[1].pipeline_attrition.total_passed_prefilter` |
| CASE_002 after ADMET | 24 | `cases[1].pipeline_attrition.total_passed_admet` |
| CASE_002 diversity clusters | 22 | `cases[1].pipeline_attrition.diversity_clusters_after_ranking` |
| CASE_002 runtime | 55.4 s | `cases[1].runtime_s` |
| CASE_002 rank-1 total-score | 0.594 | `cases[1].top_analogs_top10[0].pareto_score` |
| CASE_002 rank-1 SA | 2.97 | `cases[1].top_analogs_top10[0].sa_score` |
| Figure 5 rendered | — | `paper/figures/fig5_case_study.py` → `figures/out/fig5_case_study.{pdf,png}` |

**Phase B — Vision-aware DYRK1A re-run (with LID, new Stage-2 Tier-1 Groq Scout):**
| Phase B CASE_001 strategies | 50 (vs 20 no-LID) | `paper/experiments/exp4_case_study/results_phaseB/CASE_001.json:pipeline_attrition.total_strategies_proposed` |
| Phase B CASE_001 analogs generated | 51 (vs 149 no-LID) | `cases[0].pipeline_attrition.total_analogs_generated` |
| Phase B CASE_001 after diversity | 25 (vs 58 no-LID) | `cases[0].pipeline_attrition.diversity_clusters_after_ranking` |
| Phase B CASE_001 rank-1 total-score | 0.638 (vs 0.586 no-LID) | `cases[0].top_analogs_top10[0].pareto_score` |
| Phase B CASE_001 rank-1 SA score | 2.32 (vs 2.51 no-LID) | `cases[0].top_analogs_top10[0].sa_score` |
| Phase B CASE_001 rank-1 SMILES | `COc1ccc2c(c1)-c1cc(CN)ccc1C(C)(C)O2` (benzyl alcohol → benzyl amine) | `cases[0].top_analogs_top10[0].smiles` |
| Phase B CASE_001 wall-clock | 186.1 s (vs 139.7 s no-LID; +33 % for vision call) | `cases[0].runtime_s` |
| Phase B CASE_002 unchanged (no LID provided) | 71 → 24 → 22 (matches Phase A) | `results_phaseB/CASE_002.json` |

## §4.5 — Cross-provider model benchmark (Figure 6)

| Claim | Value | Evidence |
|---|---|---|
| 3 agent stages benchmarked | stage 2 / stage 5 / stage 6 | `paper/experiments/exp5_model_benchmark/run_benchmark.py` |
| Vision: 14 models × 8 reps on fixed DYRK1A LID | 14 × 8 = 112 calls | `paper/experiments/exp5_model_benchmark/results/stage2_summary.json` |
| Context: 11 models × 4 prompts × 3 reps | 132 calls | `paper/experiments/exp5_model_benchmark/results/stage5_summary.json` |
| Optimization: 11 models × 4 leads × 3 reps | 132 calls | `paper/experiments/exp5_model_benchmark/results/stage6_summary.json` |
| Stage 2 winner Llama 4 Scout: Jaccard 1.0, 100% JSON, 9.5 s | — | `stage2_summary.json` entry for `groq/meta-llama/llama-4-scout-17b-16e-instruct` |
| Stage 2 #2 gpt-5.4: Jaccard 0.804, 100% JSON, 9.0 s | — | `stage2_summary.json` entry for `openai/gpt-5.4` |
| Stage 5 winner gpt-5.4: rubric 0.524, 100% JSON | — | `stage5_summary.json` entry for `openai/gpt-5.4` |
| Stage 6 winner gpt-5.4: rubric 0.333, 100% JSON | — | `stage6_summary.json` entry for `openai/gpt-5.4` |
| Production code prompt verbatim used at each stage | — | Stage 2 → `prompts.py:VISION_AGENT_SYSTEM_PROMPT`; Stage 5 → `context_analyzer.py:CONTEXT_ANALYZER_PROMPT`; Stage 6 → `prompts.py:OPTIMIZATION_AGENT_SYSTEM_PROMPT` |
| Structured-output flags enable cross-provider reliability | — | `paper/experiments/exp5_model_benchmark/providers.py` (response_format / response_mime_type passes when system prompt asks for JSON) |
| Figure 6 rendered | — | `paper/figures/fig6_model_benchmark.py` → `figures/out/fig6_model_benchmark.{pdf,png}` |

## §5 — Discussion qualifiers

| Claim | Evidence |
|---|---|
| Vision-language accuracy not benchmarked against a gold standard | manuscript §5.2; consistent with `paper/experiments/exp3_vision_consistency/` measuring only self-consistency |
| Ranking is weighted scalar sum, not Pareto front | manuscript §2.8, §5.2; `backend/app/services/lead_optimizer/ranking.py:276-291` |
| No internal trained ML model | manuscript §5.2; verified by `paper/notes/01_admet.md` ("admet_ai is the upstream PyPI package; no Benchside-trained model") |
| Library validation is curator-asserted | manuscript §5.2; `validate_entire_library()` exists at `smirks_library.py:6005` but is not invoked in CI (confirmed by `grep validate_entire_library backend/tests/`) |
| Docking not in scope | manuscript §1, §5.2; verified by `paper/notes/05_remainder.md` ("no docking engine in repo") |

## Production-bug fixes surfaced and applied during the experiments

These are *real production bugs* in the codebase that surfaced during paper-grade experimental runs.
Each fix is listed for the same-commit doc-discipline rule (CLAUDE.md §Doc maintenance).

| Bug | Where | Fix | Surfaced by |
|---|---|---|---|
| `agent_rationale` set to `None` when `opt_output.expert_narrative` is None | `backend/app/services/lead_optimizer/orchestrator.py:640, 667` | `(opt_output.expert_narrative if opt_output else None) or "Strategy selection completed"` (and similarly for analog rationale) | Experiment 4 (CASE_001 + CASE_002 first run; Pydantic `ValidationError`) |
| (Inventory item, not a bug) SMIRKS library count claim was wrong in Phase 1 inventory due to a regex bug; true count is 479/22, not 167/17 | `paper/CODEBASE_NOTES.md` (correction surfaced in document) | Revert edits to `prompts.py` and `report_generator.py` to keep the correct counts | Phase 3 verification against the Python import |

## Software environment of record

| Item | Value | Source |
|---|---|---|
| RDKit | 2026.03.3 | `paper/experiments/exp1_mmp_recovery/results/pilot/manifest.json:rdkit_version` |
| Python (local Mac) | 3.11.15 | `manifest.json:python_version` |
| Python (VPS) | 3.12 | `paper/experiments/exp4_case_study/results/manifest.json:python_version` |
| Platform (local) | darwin | `manifest.json:platform` |
| Platform (VPS) | linux | `paper/experiments/exp4_case_study/results/manifest.json:platform` |
| SMIRKS library SHA-256 | (recorded in each `manifest.json`) | `manifest.json:smirks_library_sha256` |

If the SMIRKS library file is changed, every result whose manifest does not
match the new SHA-256 must be regenerated before re-citation. The manifest
files are the canonical provenance record; the figures and tables are
downstream artefacts.
