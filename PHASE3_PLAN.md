# Phase 3, Validation experiment plan (Lead Optimizer)

**Scope decision:** Option B, focused paper on the Lead Optimizer.
**Pre-requisite fix:** None needed, the SMIRKS library count was verified to be **479 entries across 22 distinct categories** (CLAUDE.md and the prompts were correct). The Phase 1 inventory claim of "167 entries" was a regex bug, the count pattern required underscores between letters and digits, but ~312 entries use the form `POLA019` / `NHEX001` (no underscore). My earlier edits to `prompts.py:199` and `report_generator.py:1037` were reverted. Audited counts:
- Total entries (Python import): 479
- Distinct `category` field values: 22 (aromatic_ring_swaps 54, amine_modifications 48, o_substitutions 30, carbonyl_modifications 30, cns_penetration 26, nitrogen_heterocycle_swaps 25, carboxylic_acid_replacements 20, amide_bond_replacements 20, metabolic_stability 20, halogen_substitutions 20, bioisosteric_replacements 20, aromatic_substitutions 20, steric_shielding 20, polarity_adjustments 20, benzylic_modifications 15, ether_modifications 15, ester_modifications 15, carbocyclic_replacements 15, nitrile_modifications 14, sulfonamide_modifications 12, sulfonyl_modifications 10, catechol_transformations 10).
- All 479 entries marked `validated=True` (curation assertion, not RDKit-runtime gate, `validate_entire_library()` exists at `smirks_library.py:6005` but is not called in production code).

**Standing rule:** Every result lands as raw CSV/JSON under `paper/experiments/results/<exp-id>/`, runtime + git SHA logged in a sidecar file. No number appears in the paper without a script in `paper/experiments/` that reproduces it.

---

## Environment strategy

Local Mac (Python 3.14.5, zero scientific packages installed): bootstrap a Python 3.12 venv at `paper/.venv/` because Python 3.14 is too new for some wheels. Install in tiered order:

| Tier | Packages | Size | Used for |
|---|---|---|---|
| 1 (small, fast) | `rdkit`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `tqdm` | ~600 MB | Exp 1, 2, structural analysis, figures |
| 2 (medium) | `mmpdb`, `syba`, `requests` | ~100 MB | Exp 1 MMP enumeration, SYBA scoring |
| 3 (heavy, only if needed locally) | `admet_ai`, `chemprop`, `torch` | ~3 GB | Exp 2 ADMET re-prediction (alternative: use VPS) |
| 4 (TDC) | `PyTDC` | ~500 MB | Original Phase 3 priority 1, TDC ADMET benchmark; deferred behind Lead-Optimizer-specific experiments |

VPS (`pharmgpt-api` on Contabo) used for: end-to-end pipeline runs (Exp 4), vision-agent inference (Exp 3 evaluation phase).

Free disk locally: 15 GB. Sufficient for Tier 1+2; Tier 3 ADMET will likely live on VPS.

---

## Experiment 1, MMP recovery rate (priority 1)

### Claim the paper makes
*"On matched-molecular pairs from public bioactivity data, the SMIRKS-driven permutation engine recovers the empirically-observed improving transformation in the top-K analogs at rate X. Recall@1=…, recall@10=…, recall@100=…"*

This is the single strongest paper-grade quantitative claim the Lead Optimizer can carry, because the answer key (which analog actually improved which property) is in the public data.

### Data source, three candidates, picking 1
1. **ChEMBL MMP via MMPDB index (preferred)**, build an MMP database from ChEMBL-32 small-molecule bioactivity using `mmpdb index` on the SMILES list, then filter pairs with a measured ΔLogP, Δactivity, or Δsolubility ≥ threshold. Fully reproducible, citable, widely understood baseline.
2. **Hussain & Rea 2010 standardized MMP set** (~20K pairs from public sources). Pre-built. Older but well-cited.
3. **GuacaMol MMP test set**, smaller (~5K pairs) but framed for generation benchmarks. Useful as a sanity check.

**Default:** Use MMPDB-derived ChEMBL pairs with `--max-variable-heavies 10 --min-radius 0`. Cap at 2000 pairs for paper Phase 3; full set for supplementary.

### Method
For each MMP `(A, B)` where B is the empirically-better analog:
1. Call the pipeline's permutation engine on A with all 479 SMIRKS allowed (no Vision Agent, use a synthetic "all groups TARGET" classification to isolate the SMARTS-driven contribution).
2. Compute Tanimoto similarity (Morgan/ECFP4, 2048 bits) between B and each generated analog.
3. Rank analogs by Tanimoto-to-B AND by the pipeline's own ranking.
4. Report recall@K for K ∈ {1, 5, 10, 50, 100}.

### Ablations
- **+ Murcko gate** vs without, quantifies the soft scaffold gate's contribution
- **+ chemistry validator** vs without, quantifies the validator's contribution
- **+ Vision Agent** (synthetic ground-truth classification for the LID-equipped subset), quantifies vision-aware site selection

### Hardware / runtime
Local Mac (RDKit only, no LLM). Estimated runtime: ~30 s per MMP × 2000 = ~17 hours single-threaded; ~3 hours with multiprocessing (Pool(8)). Run overnight if needed.

### Output
- `paper/experiments/results/exp1_mmp_recovery/pairs.csv`, input MMP set
- `paper/experiments/results/exp1_mmp_recovery/analogs_<pair_id>.parquet`, per-pair generated analogs with SMILES, Tanimoto-to-B, rank
- `paper/experiments/results/exp1_mmp_recovery/recall.csv`, recall@K summary
- `paper/experiments/results/exp1_mmp_recovery/ablation.csv`, gate-on/off comparison
- `paper/experiments/results/exp1_mmp_recovery/manifest.json`, git SHA, runtime, MMPDB version, RDKit version, SMIRKS file SHA-256

### What "good" looks like
For a paper that survives review, recall@100 ≥ 30% on the 1- and 2-edit MMP subset would land well. Recall@10 ≥ 10% would land *very* well. If recall@100 < 5% I would say so plainly and call the experiment a negative result.

---

## Experiment 2, Scaffold preservation + structural alert audit (priority 2)

### Claim the paper makes
*"On 250 diverse leads across kinase, GPCR, protease, and ion-channel target classes, generated analogs preserve the Bemis–Murcko scaffold at rate X (vs Y for a SMIRKS-baseline without the soft Murcko gate, and Z for Reinvent-style RL generation). PAINS-alert rate is A%, Brenk-alert rate is B%."*

### Data source
**ChEMBL-curated 250-lead set**, sample 250 unique scaffolds from ChEMBL drug-like compounds (`mw ≤ 500`, `logP ≤ 5`, no PAINS in the input). Stratified by target family (kinase 80, GPCR 60, protease 40, ion-channel 30, transcription factor 20, other 20). Save SMILES + ChEMBL ID + target class as `seed_leads.csv`.

### Method
For each lead:
1. Run permutation with default SMIRKS settings, soft Murcko gate ON
2. Run permutation with Murcko gate OFF (ablation)
3. Compute per-analog metrics:
   - Bemis–Murcko scaffold SMILES (RDKit `MurckoScaffold.MurckoScaffoldSmiles`)
   - PAINS flag (RDKit's three PAINS catalogs combined)
   - Brenk flag (RDKit `FilterCatalog.BRENK`)
   - Lipinski Ro5 violations
   - Heavy-atom count delta vs lead
   - LogP delta vs lead

### Baselines
- **SMIRKS no-Murcko-gate** (ablation, fair internal comparison)
- **Reinvent v3.2** with default reagent-based generation (if installable; if not, use MOSES default char-RNN on the same 250 leads as seeds)
- **GuacaMol MOSES char-RNN baseline** (fallback; pre-trained model from MolecularSetsLib)

### Hardware
Local Mac (RDKit) for Benchside pipeline. Reinvent/MOSES baseline: VPS or fresh venv on Mac.

### Output
- `paper/experiments/results/exp2_scaffold_alerts/seed_leads.csv`
- `paper/experiments/results/exp2_scaffold_alerts/analogs.parquet`, full generated set, one row per analog, with all metrics
- `paper/experiments/results/exp2_scaffold_alerts/summary.csv`, per-method aggregate (scaffold-preserved %, PAINS %, Brenk %, mean ΔLogP, mean Δ HA-count)
- `paper/experiments/results/exp2_scaffold_alerts/per_target_class.csv`, same stratified by target class
- `paper/experiments/results/exp2_scaffold_alerts/manifest.json`

### Runtime estimate
~10 s per lead × 250 = 40 min single-threaded; ~10 min with multiprocessing.

---

## Experiment 3, Vision Agent accuracy on held-out LIDs (priority 3)

### Claim the paper makes
*"On a held-out set of 50 ligand-interaction diagrams from PDB entries, the Vision Agent correctly classifies binding-contact (RESTRICTED) atoms at precision P, recall R, F1 F. The chemistry-validity validator removes X chemically-impossible classifications per LID on average."*

### Data construction (the hard part)
1. Sample 50 PDB entries with bound small-molecule ligands and well-resolved binding sites (resolution ≤ 2.5 Å), across diverse target classes
2. For each, render the LID using **PoseView** or **PLIP** (both open-source)
3. Hand-annotate the ground-truth RESTRICTED atoms (those making H-bond, π-stack, salt-bridge, or close-hydrophobic contact with protein residues), this is the labour-intensive step, ~2 hours total
4. Save as `gold_lids/<pdb_id>.png` + `gold_lids/<pdb_id>.json` (per-atom labels)

### Method
1. Run Vision Agent on each gold LID via the VPS pipeline
2. Compute per-atom precision, recall, F1 on the RESTRICTED classification
3. Report per-target-class breakdown
4. Report ablation: with vs without chemistry validator (i.e., what fraction of impossible-chemistry classifications would have leaked without it)

### Hardware
VPS, needs the vision-agent provider chain.

### Output
- `paper/experiments/results/exp3_vision_accuracy/gold_lids/`, input set
- `paper/experiments/results/exp3_vision_accuracy/predictions.json`, vision-agent outputs
- `paper/experiments/results/exp3_vision_accuracy/per_lid_metrics.csv`
- `paper/experiments/results/exp3_vision_accuracy/summary.csv`, overall + per-class P/R/F1
- `paper/experiments/results/exp3_vision_accuracy/validator_impact.csv`, chemistry-validator drop count per LID
- `paper/experiments/results/exp3_vision_accuracy/manifest.json`

### Risk
Hand annotation is labour-intensive. **Fallback:** use 20 LIDs (not 50) and report it transparently in methods; or use programmatically-derived RESTRICTED atoms from PLIP's interaction output as silver-standard labels (citing PLIP's own validation).

---

## Experiment 4, End-to-end case study (priority 4)

### Claim the paper makes
*"A complete run of the lead-optimization pipeline on a representative kinase (DYRK1A) and a representative bacterial target (PBP2a) yields N validated analogs with median SYBA score X, M with all-pass ADMET, and Y with conserved pharmacophore. Top-10 candidates by total-score are presented in Table N."*

### Method
- Pick 2 leads:
  - **DYRK1A:** Compound 25014 (user precedent in CLAUDE.md). PDB-derived LID available from prior session.
  - **PBP2a:** Pick a literature-known starting compound (e.g. ceftaroline or a DOS scaffold from a recent ACS Infect. Dis. paper). User confirms.
- Run full 12-stage pipeline on VPS with default settings
- Capture stage-by-stage attrition: input → vision restricted → permutation analogs → pre-filter survivors → ADMET survivors → SYBA-ranked top-K
- Manually inspect top-10 for medicinal-chemistry sensibility (paper would frame as "qualitative inspection by domain reader", flag that this is *not* experimental validation)

### Hardware
VPS.

### Output
- `paper/experiments/results/exp4_case_study/DYRK1A/stages.json`, per-stage counts + samples
- `paper/experiments/results/exp4_case_study/DYRK1A/top10.csv`
- `paper/experiments/results/exp4_case_study/PBP2a/stages.json`
- `paper/experiments/results/exp4_case_study/PBP2a/top10.csv`
- `paper/experiments/results/exp4_case_study/manifest.json`

### Runtime
~30–60 min per target run.

---

## Experiment 5 (stretch), TDC ADMET benchmark

Original Phase 3 priority 1, demoted to stretch because the Lead Optimizer paper doesn't need it (ADMET is the screening stage, cited as upstream `admet_ai`). Still useful as supplementary because it gives the reviewer reassurance about the screening stage's reliability.

### Method
Standard TDC ADMET Benchmark Group, scaffold splits, prescribed metrics per task. Use `from tdc.benchmark_group import admet_group`. Compare engine's numbers to upstream `admet_ai` published values + TDC leaderboard.

### Hardware
Local (Mac) with Tier 3 deps, or VPS.

### Output
`paper/experiments/results/exp5_tdc_admet/per_task.csv`, our AUROC/MAE per task next to leaderboard

---

## Sequencing and dependencies

```
[venv bootstrap] ──┬──> [Exp 1: MMP recovery] ──> figure 2 (recall curves)
                   ├──> [Exp 2: scaffold + alerts] ──> figure 3 (preservation bars)
                   │
[VPS setup]      ──┼──> [Exp 3: vision accuracy] ──> table 1 (P/R/F1)
                   └──> [Exp 4: case study] ──> figure 4 (workflow trace), table 2 (top 10)

[Exp 5: TDC], runs in parallel anytime; supplementary
```

**Critical path:** venv bootstrap → Exp 1 → Exp 2 (Tier-1 paper claims). 1–2 days.
**Parallel:** Exp 3 gold-set construction (manual). 0.5 day.
**Sequential:** Exp 4 case study (after Exp 3 confirms vision-agent on diverse scaffolds).

---

## What I'm about to do, in order

1. Bootstrap `paper/.venv/` (Python 3.12, Tier 1 + Tier 2 packages)
2. Build the Experiment 1 driver script (`paper/experiments/exp1_mmp_recovery/run.py`), pure RDKit, no LLM
3. Run the experiment on a 200-pair pilot (~20 min) and inspect results before committing to the full 2000-pair run
4. Report back with pilot results and pause for your sanity-check before running everything else

---

## Open user decisions

These I'd like a one-liner on before I run anything long, but defaults are flagged so I can move:

| Decision | Default if you don't redirect | When I need an answer |
|---|---|---|
| MMP source for Exp 1 | ChEMBL via `mmpdb index` (build it ourselves) | Before Exp 1 driver |
| Pair-set size for Exp 1 | 200 pilot → 2000 full | After pilot |
| Baseline for Exp 2 | Reinvent v3.2 if installable, else MOSES char-RNN | Before Exp 2 |
| LID gold-set size for Exp 3 | 50 hand-labelled (target); 20 + PLIP silver standard as fallback | Before Exp 3 |
| Case-study targets for Exp 4 | DYRK1A (user precedent) + PBP2a | Before Exp 4 |
| Run TDC benchmark as supplementary? | Yes, in parallel | Anytime |
| Update CLAUDE.md "Recent fixes" row for the SMIRKS-count fix? | Per project rule: yes, in the same commit | When committing |

If silent, I take the defaults and we go.
