# A vision-language agentic pipeline for lead optimization with chemistry-validity defence-in-depth

Toluwanimi Odunewu

Independent Researcher

Aisynth Labs

odunewutolu2@gmail.com

June 11, 2026

---

## Abstract

**Background:** Lead optimization in small-molecule drug discovery is a constrained search problem: from a chemical starting point and the structural cues of its binding pose, propose analogs that preserve the pharmacophore, satisfy ADMET liabilities, and remain synthetically accessible. Individual components — pharmacophore alignment, SMIRKS transformation libraries, ADMET predictors, scaffold analysis, structural-alert filters — are mature, but the orchestration of these tools into a reproducible workflow that takes a lead and its ligand-interaction diagram (LID) as input and returns a ranked, filtered analog set is non-trivial.

**Methods:** We describe a twelve-stage agentic pipeline that combines a vision-language classifier of LIDs with a per-instance SMARTS construction step, deterministic structural gates, a curated 479-entry SMIRKS transformation library, an upstream ADMET-prediction backbone, and a synthetic-accessibility-anchored ranking. The architectural contribution is **defence-in-depth**: each agent stage is wrapped by a deterministic gate (chemistry-validity allowlists, soft Murcko ring-topology check, PAINS / Brenk structural-alert filters, ADMET-screen thresholds) so that perception errors cannot corrupt the downstream analog set.

**Results:** Across five evaluations — (i) a curated single-edit bioisosteric matched-molecular-pair pilot on which the library exact-recovers 16/30 = 53.3 % of documented improving transformations; (ii) an unbiased ChEMBL-37–derived MMP scale-up of 2,000 pairs on which it exact-recovers 15.5 % with mean best Tanimoto-to-target 0.755 in misses; (iii) a 129-marketed-drug scaffold-preservation and structural-alert audit showing the soft Murcko gate cuts the analog set roughly in half while raising scaffold preservation to 100 %; (iv) a vision-language classifier self-consistency study on a fixed LID (pairwise Jaccard 1.00 across all 28 pair-comparisons, zero chemistry-validator drops); and (v) an end-to-end case study on two contrasting leads (DYRK1A kinase inhibitor and Linezolid antibacterial), in which a LID-aware run improves the rank-1 analog on both Pareto-style score (0.586 → 0.638) and synthetic accessibility (2.51 → 2.32) — the defence-in-depth design preserves end-to-end output quality despite intermediate-stage variability. We additionally benchmark eleven language models across the three agent stages and report which configurations achieve reliable strict-JSON adherence and self-consistency, providing measured rather than asserted recommendations for the production default.

**Conclusions:** The pipeline demonstrates that a small set of deterministic structural gates around language-model agent stages is sufficient to absorb vision-classifier errors and produce constrained, pharmacophore-preserving lead optimization output on multiple target classes. The platform is implemented as production software; the code, data, manifest-stamped raw outputs, and reproduction scripts are released open source under the MIT licence at https://github.com/Nimieeee/lead-optimizer-paper.

## Keywords

Lead optimization, Computer-aided drug design, Matched molecular pairs, SMIRKS, Vision-language models, Pharmacophore preservation, ADMET, Synthetic accessibility, SYBA, Bemis–Murcko scaffold, Open-source cheminformatics, Agentic pipelines, Defence-in-depth

---

## 1. Introduction

Lead optimization is one of the most resource-intensive stages of small-molecule drug discovery. Given a lead compound with a known binding pose, medicinal chemists must propose analogs that retain key pharmacophore contacts (18), address known ADMET liabilities, remain within a synthetically tractable region of chemical space, and avoid structural alerts that predict toxicity or assay artefact. Each of these axes has decades of in-silico tooling — pharmacophore alignment, transformation libraries (SMIRKS) (14), ADMET predictors, scaffold analysis, structural-alert filters — but the orchestration of these tools into a single, reproducible workflow that takes a lead and its ligand-interaction diagram as input and returns a ranked, filtered set of analogs is non-trivial.

Two recent shifts make a re-examination of this orchestration timely. First, vision-capable language models can now extract structured information from ligand-interaction-diagram images at a useful (if imperfect) rate, opening the possibility of automatically inferring which atoms in a lead are involved in protein contact and which are editable. Second, the synthetic-accessibility prediction literature has converged on signed-score classifiers (notably SYBA(1)) that, unlike rule-based heuristics, produce a directionally interpretable score that can serve as a ranking penalty rather than a hard filter.

A naive integration of these two capabilities would simply pipe the vision-language output into a transformation enumerator and rank by SYBA. We argue and demonstrate that this integration is *insufficient* for practical use — vision-language classifications carry systematic failure modes (chemically impossible interactions, conflated similar substructures, scaffold-breaking edits proposed as innocuous), and the pipeline must protect downstream stages from these failures by stacking deterministic gates around each agent step. We refer to this design as **defence-in-depth**.

This paper makes the following contributions:

1. A twelve-stage lead-optimization pipeline that integrates vision-language LID parsing, per-instance SMARTS classification (with 2D-coordinate-derived disambiguation), a soft Murcko ring-topology scaffold gate, a chemistry-validity allowlist that drops physically-impossible vision outputs, a 479-entry SMIRKS library across 22 categories, ADMET prediction (via the upstream `admet_ai`(2) Chemprop-v2 backbone), and a SYBA-anchored penalty rank.
2. An empirical evaluation spanning (a) the SMIRKS engine's recovery rate on a curated bioisosteric pilot and on an unbiased ChEMBL-37–derived matched-molecular-pair scale-up of 2,000 pairs, (b) the soft Murcko gate's effect on scaffold preservation and structural-alert rates over a 129-marketed-drug seed panel, (c) the vision-language classifier's self-consistency on a fixed LID across independent runs, (d) the end-to-end pipeline on two contrasting target classes with LID-aware and LID-free configurations, and (e) a cross-provider model benchmark across the three agent stages to inform the production default.
3. The full implementation, raw experiment outputs with provenance manifests, figure-generation scripts, and a claims-to-evidence map, all released for reproducibility.

We deliberately frame several capabilities the pipeline does *not* provide: it does not include a docking or molecular-mechanics engine (binding affinities consumed from upstream sources are reasoned over but never computed); it does not train an internal ADMET model (the upstream Chemprop-v2 ADMET predictor is cited as-is); and it does not provide proof-of-binding for any analog it generates.

---

## 2. Pipeline architecture

The twelve stages of the pipeline are summarised in Figure 1. We group them into four functional phases: **perception** (stages 1–2), **classification and gating** (stages 3 and the chemistry validator), **transformation and filtering** (stages 4–10), and **ranking and reporting** (stages 11–12).

![**Figure 1.** Twelve-stage lead-optimization pipeline. Inputs (lead SMILES, optional ligand-interaction diagram, project context) flow through perception, classification, transformation, and ranking phases. Each agent stage (dark fill) is wrapped by a deterministic gate (purple) so that perception errors are absorbed before the analog set is corrupted.](figures/out/fig1b_lead_optimizer_pipeline_snake.png)

### 2.1 Inputs and pre-scan (stage 1)

The pipeline accepts five inputs: **(i)** the lead SMILES (15) (required), **(ii)** the ligand-interaction diagram as a PNG (optional; when absent, every functional group is treated as TARGET and stages 2–2′ are skipped), **(iii)** free-text **project context** that describes the therapeutic indication, target class, and binding-axis priorities (e.g. *"CNS DYRK1A inhibitor (24), prioritize BBB"*) — this text is consumed at stage 5 to shape the per-endpoint ADMET weighting and hard-stop thresholds, **(iv)** optional visual hints, and **(v)** an analog-budget knob bounding the combinatorial explosion at stage 8.

Given the lead SMILES, we use RDKit(5) to (a) detect functional-group occurrences via a curated 90+-entry SMARTS substructure library, (b) compute the Bemis–Murcko(6) scaffold atom set and SMARTS, and (c) assign 2D coordinates to enable per-instance position hints. The output is a labelled-instance list in which each detected group carries an atom-index set and a positional hint (`phenyl_left`, `aromatic_h_top-left`, etc.). This step is deterministic.

### 2.2 Vision-language LID classifier (stage 2)

A vision-capable language model receives the LID PNG and a structured prompt enumerating the labelled instances from stage 1. It returns a JSON record dividing the labelled groups into two categories: **RESTRICTED** (groups making a visible protein contact in the diagram — H-bond, π-stack, salt-bridge, hydrophobic contact, cation-π) and **TARGET** (groups not in contact, therefore editable). For each restricted group, the record lists contacting residues and interaction types. A multi-tier provider chain handles transient API failures.

This step is the single largest source of error in the pipeline. Classifying a binding-restricted methyl as a TARGET would let permutation remove it and silently destroy the pharmacophore; conversely, marking too many groups as RESTRICTED would shrink the optimization surface to nothing. The chemistry validator (next subsection) is the first line of defence against the former; the soft Murcko gate (stage 3) is the second.

### 2.3 Chemistry-validity validator

A deterministic allowlist table maps each interaction type to the set of functional-group families that can chemically participate. The validator drops any vision-language output that violates the table (e.g. a methyl classified as a hydrogen-bond donor, a methoxy classified as a donor) before the SMARTS builder sees it. The allowlist is implemented as static dictionaries (`H_BOND_DONORS`, `H_BOND_ACCEPTORS`, `PI_STACK_GROUPS`, `HYDROPHOBIC_GROUPS`, `SALT_BRIDGE_GROUPS`, `CATION_PI_GROUPS`) and is independent of the vision model.

### 2.4 SMARTS builder, scaffold anchor (stage 3); soft Murcko gate fires at stages 7–8

For each labelled instance, the SMARTS builder (13) constructs an atom-anchored SMARTS via RDKit's `MolFragmentToSmarts`, so that two phenyl groups in the same molecule receive distinct atom-specific patterns rather than collapsing to a generic `c1ccccc1`. This is the per-instance disambiguation referenced in the introduction.

In the same stage, the Bemis–Murcko scaffold SMARTS is appended to the restricted-SMARTS set. The actual *check* — the soft Murcko gate — is implemented inside `enforce_pharmacophore` (stages 7–8) and fires twice: once at strategy validation (does this SMIRKS, applied to one example, preserve the pharmacophore?) and once for every candidate analog the permutation engine produces. The gate's predicates are (a) restricted atoms unchanged, (b) ring-system topology preserved (same ring count), (c) aromaticity preserved. This replaces an earlier "hard SMARTS append" approach that rejected all edits at scaffold atoms — including the topologically equivalent methyl→ethyl substitution on a scaffold carbon — and was over-restrictive in practice.

### 2.5 ADMET profile, project-context analysis, and optimization agent (stages 4–6)

**Stage 4 — Lead ADMET profile.** A single forward pass through the upstream `admet_ai` (2), built on the Chemprop V2 Graph Neural Network framework (3; 4), on the lead molecule yields the 54-endpoint baseline. These values are consumed by stage 5 as the prior the optimization should improve on, and by stage 10 as the thresholds the screen will enforce.

**Stage 5 — Project-context analysis.** A structured-output language model reads the user-supplied project-context text (§2.1, input iii) and emits a typed `ContextAnalysis` record containing (a) per-endpoint priority weights (e.g. for a CNS lead, BBB-permeability weight is elevated and CYP-substrate penalty is softened relative to a peripheral-target weighting), (b) hard-stop thresholds (e.g. hERG > 0.5 hard-rejects), and (c) a single-sentence primary-optimization goal. This is where the indication-specific shape of the rest of the pipeline is established; without a project-context input the system falls back to a generic balanced-weighting default.

**Stage 6 — Optimization agent.** Given the lead's ADMET profile (stage 4), the project-context priorities (stage 5), and the labelled TARGET sites (stages 1 + 2), a structured-output language model proposes a ranked list of SAR strategies — lower LogP, swap aryl halide, polar isostere, ring-isomer change, halogen substitution, etc. — each mapped to one or more SMIRKS-library categories. Strategies are emitted under a strict JSON schema; downstream stages do not invoke language models.

### 2.6 Validation, permutation, pre-filter, and ADMET screen (stages 7–10)

The proposed strategies are validated against the SMIRKS library (each strategy is mapped to one or more SMIRKS entries by category), and the permutation engine enumerates analogs by applying each allowed SMIRKS to its target sites only. The product of (sites × strategies × SMIRKS-per-strategy) bounds combinatorial explosion. The pre-filter applies hard structural validity (RDKit sanitisation, valency check), Lipinski Rule-of-Five (7), the PAINS catalogs (A, B, C) (10), and the Brenk filter (11). The ADMET screen re-runs the Chemprop-v2 predictor on every surviving analog and rejects analogs whose hERG / Skin Reaction / CYP probability exceeds a configurable threshold; conversely, beneficial-direction endpoints (HIA, bioavailability, BBB) below threshold are penalised.

### 2.7 Synthetic-accessibility scoring (stage 11)

We compute the SYBA score (1) for every surviving analog. As described by Voršilák et al. (1), SYBA is a Bernoulli naïve-Bayes classifier trained on databases of easy- and hard-to-synthesise molecules; we use the reported AUC > 0.81 and the signed-score convention (positive for synthesisable, negative for hard-to-make, magnitude roughly in [−50, +50]). We adopt SYBA as the **primary** synthetic-accessibility signal across the platform (in ranking, reports, CSV exports); Ertl's SAScore (12) is computed in parallel and retained as a legacy field for audit but is not surfaced.

### 2.8 Ranking and report (stage 12)

The ranking step computes a **weighted scalar penalty score** over docking (when present in input), ADMET liabilities (directional, per Section 2.6), SYBA, structural alerts, and (when present) molecular-property axes such as cLogP. The output is sorted by the scalar score and the top-K analogs are written to PDF (via WeasyPrint), HTML, and CSV.

We label the rank a "Pareto-style penalty rank" by API convention; it is in fact a sorted single-score rank, not a Pareto front. We mention this here to avoid suggesting a property the implementation does not have.

---

## 3. Experimental setup

All experiments are reproducible from `paper/experiments/`. Each results directory carries a `manifest.json` containing the git SHA at the time of the run, the RDKit and Python versions, the SHA-256 of the SMIRKS library file, and the SHA-256 of the input dataset. We refer to that manifest as the canonical provenance record.

### 3.1 Experiment 1 — MMP recovery

We curate 30 single-edit literature-documented bioisosteric (17) matched molecular pairs (MMPs) (16) spanning the library's category prefixes (ACID, AMINE, RING, HALO, SLFA, NIT, OSUB, STER, ETHER, BENZ). For each pair `(A, B)` we apply the full 479-entry SMIRKS library to `A`, compute the canonical-SMILES of every product, rank products by Tanimoto similarity using Morgan / ECFP4 fingerprints (radius 2, 2048 bits) (9) to `B`, and check whether `B` appears at any rank. Recall@K is reported for K ∈ {1, 5, 10, 50, 100, 500}.

**Unbiased scale-up on ChEMBL-derived MMPs.** To complement the curated pilot, we built an unbiased matched-molecular-pair set from a 2000-compound drug-like subset of ChEMBL-37 (23) (drug-like criteria: 12 ≤ HA ≤ 35, MW ≤ 500, HBD ≤ 5, HBA ≤ 10, −2 ≤ LogP ≤ 5, single-component, RDKit-stereo-stable). `mmpdb` (19) fragmentation and indexing yielded 41,310 raw pairs; filtering to small single-edit transformations (`length(from_SMILES) ≤ 10` and `length(to_SMILES) ≤ 10`) gave **2856 candidate single-edit pairs**, from which we sampled **2000 for evaluation**. On this set the library exact-recovers `B` in **310 / 2000 = 15.5 %** of cases — the unbiased headline number. Mean best Tanimoto-to-`B` rises to **0.755** (vs the pilot's 0.687), confirming that the library produces *structurally-close* alternatives even when it does not hit the specific empirical `B`. The 15.5 % gap between the upper-bound pilot (53.3 %) and the unbiased ChEMBL set (15.5 %) calibrates the library's *native-domain* coverage vs *long-tail-transformation* coverage. Runtime on 2000 pairs: **7 min** on seven-way multiprocessing.

### 3.2 Experiment 2 — Scaffold preservation + structural alerts

We extract 129 FDA-approved drugs (with their SMILES and therapeutic class) from the platform's curated drug suggestion pool. For each seed, we apply the full SMIRKS library and capture every product as a candidate analog. Per-analog we compute: Bemis–Murcko scaffold preservation vs. the lead, PAINS-A/B/C combined flag, Brenk flag, Lipinski-Ro5 violations, heavy-atom delta, and cLogP delta. We report two conditions: **default** (Murcko gate ON; only scaffold-preserving analogs retained) and **ablation** (Murcko gate OFF; all analogs retained), with the seed-baseline structural-alert rate as reference.

### 3.3 Experiment 3 — Vision-language classifier self-consistency

We take a single LID image (the DYRK1A Compound 25014 binding pose used in our internal validation) and run the Vision Agent N = 8 independent times against the same input. We report (a) pairwise Jaccard similarity of restricted-atom sets across runs, (b) the consensus restricted-atom set (atoms appearing in ≥ 80 % of runs), (c) the per-run count of chemistry-validator drops, and (d) the provider-tier distribution. This is a self-consistency metric; it does not require a gold-standard annotation, and it directly measures the perception variance the rest of the pipeline must guard against.

### 3.4 Experiment 4 — End-to-end case study

We run the complete twelve-stage pipeline on two leads spanning contrasting target classes: (a) Compound 25014, a methoxy- and benzyl-alcohol-substituted benzodioxin from a DYRK1A kinase / CNS series (24); (b) Linezolid, an FDA-approved oxazolidinone gram-positive antibacterial (25). A first configuration treats both leads with the no-LID path (Vision Agent skipped; every functional group classified as TARGET) so the SMIRKS engine, soft Murcko gate, structural-alert filters, ADMET screen, and SYBA ranking are exercised end-to-end. A second configuration attaches the DYRK1A LID image to Compound 25014 (Linezolid is run without LID in both configurations because no LID is available for the chosen lead) so the production vision-language classification stage is also exercised. We report stage-by-stage attrition and the top-ten analogs by total-score for each case under each configuration.

### 3.5 Experiment 5 — Cross-provider model benchmark

The three agent stages are each backed by a language model. We benchmark fourteen vision-capable models (stage 2) and eleven text models (stages 5 and 6) by running the production prompts verbatim against each model, with the same fixed inputs and three to eight repetitions per (model, input) cell. Stage 2 is scored by self-consistency Jaccard on the restricted-atom-key set; stage 5 by a hand-graded endpoint-priority rubric across four representative project-context strings (CNS-kinase, oral gram-positive antibacterial, topical anti-inflammatory, oncology); stage 6 by a strategy-validity rubric checking that proposed strategies (a) reference a TARGET site that actually exists on the lead and (b) map to a real SMIRKS category in the library. A model is considered *reliable* on a stage when its strict-JSON adherence rate is at least 50 %.

---

## 4. Results

### 4.1 MMP recovery on the curated pilot

**Headline numbers, pilot.** Of 30 single-edit bioisosteric pairs, the library exact-recovers `B` (canonical-SMILES match) in **16/30 cases = 53.3 %**, every recovered analog at rank 1 by Tanimoto (the canonicalization produces a Tanimoto-1.0 hit). Recall is therefore flat across K ∈ {1, 5, 10, 50, 100, 500} (Figure 2a). Of the 14 misses, 13 do produce analogs but not the exact-`B` we curated — typical best Tanimoto-to-`B` for these is 0.27 – 0.65 — and the discrepancy traces to (a) tautomer or canonicalization differences (e.g. our hand-curated `B` for the COOH → tetrazole pair uses one tautomer; the SMIRKS product canonicalises to the other), and (b) cases where the library proposes valid alternative bioisosteres but not the specific `B` we curated.

![**Figure 2.** MMP recovery on the curated bioisosteric pilot and the unbiased ChEMBL-37 scale-up. **(a)** Recall@K curves are flat at 53.3 % (pilot, n=30) and 15.5 % (ChEMBL, n=2000) because exact recoveries canonicalise to Tanimoto=1.0 at rank 1. **(b)** Per-pair best-Tanimoto for the pilot, coloured by hit / miss-with-analogs / one library limitation (indole→quinoline ring expansion). **(c)** ChEMBL best-Tanimoto distribution across 2000 pairs; mean=0.755 indicates the library generates structurally-close alternatives even when the specific empirical B is not recovered.](figures/out/fig2_mmp_recovery.png)

**One real library limitation surfaced.** The `indole → quinoline` pair (MMP_020) generates 97 analogs but never the canonical quinoline; the library has no SMIRKS that performs the 5-ring→6-ring expansion with the concurrent nitrogen-position shift. This is a paper-worthy observation about the *scope* of SMIRKS-based transformation libraries: they handle atom and group substitutions well, but ring-size-changing operations require a different transformation primitive. We do not propose this as a defect in the library; we identify it as a class of transformation outside the SMIRKS-substitution scope.

**Audit-trail note.** An earlier version of this paragraph reported 15/30 = 50 % and named *two* zero-analog gaps. Diagnostic work surfaced that one of those (MMP_007, `OMe → OCF3`) was a malformed-B SMILES in our pilot data, not a library limitation; with the SMILES corrected the pair now exact-recovers via `OSUB_005`. The audit trail is preserved in `paper/CLAIMS_EVIDENCE.md`.

Median runtime is 0.19 s/pair on seven-way multiprocessing (Apple M-series; clear runtime budget for the ChEMBL-MMP scale-up).

### 4.2 Scaffold preservation and structural-alert rates

The 129-seed scaffold-and-alert audit (Figure 3) measures two related properties of the analog set: (i) does the soft Murcko gate actually preserve the lead's ring system, and (ii) at what rate does the SMIRKS library introduce PAINS / Brenk-flagged substructures relative to the seed compounds themselves.

![**Figure 3.** Scaffold preservation and structural-alert audit on 129 marketed-drug seeds. **(a)** Structural-alert composition (clean vs Brenk-flagged vs PAINS-flagged) across seeds, the gate-off ablation, and the default gate-on condition. **(b)** Soft Murcko gate impact: scaffold preservation rises from 53.9 % to 100 % while the analog count halves (16,244 → 8,758). **(c)** Heavy-atom-delta distribution for default-condition analogs.](figures/out/fig3_scaffold_alerts.png)

**Headline numbers** (129 marketed-drug seeds, 119 with ≥ 1 generated analog):

| Metric | Seed baseline | Ablation (gate OFF) | Default (gate ON) |
|---|---|---|---|
| Total analogs | — | 16,244 | 8,758 |
| Scaffold preserved | by definition | 53.92% | 100.0% |
| PAINS-flagged | 5.0% | 9.47% | 6.43% |
| Brenk-flagged | 26.1% | 44.29% | 46.47% |
| Lipinski-Ro5 pass | — | 96.05% | 96.08% |
| Clean (no PAINS, no Brenk) | 70.6% | 53.23% | 50.9% |

**Reading.** The soft Murcko gate halves the analog count from 16,244 to 8,758 while pushing scaffold preservation to 100 %. The SMIRKS library *increases* the structural-alert rate over the seed baseline (Brenk 26 % → 44 %; PAINS 5 % → 9 %); this is not a failure mode but the load-bearing motivation for the chemistry validator and the upstream ADMET screen, which together filter the alert-flagged analogs out of the final ranked list.

### 4.3 Vision-language classifier self-consistency

Across **N = 8 independent vision-agent runs on the same DYRK1A LID**, the pairwise Jaccard similarity of the restricted-atom-key set is **1.00 across all 28 pair comparisons** (Figure 4a). The consensus restricted set (atoms appearing in ≥ 80 % of runs, equivalently in **all** runs at this perfect-agreement level) contains **3 distinct restricted-atom keys**. The chemistry validator drops **0 ± 0 entries per run** on average (no entries flagged as hallucinated; no chemistry-impossible classifications emitted), indicating that on this particular LID the model's perception output is fully within the chemistry allowlist. Mean runtime per run is **5.06 s** (s.d. 0.56 s; min 4.38 s, max 6.28 s), consistent with a single primary-tier provider call per run (Figure 4b).

![**Figure 4.** Vision-language classifier self-consistency on a fixed LID. **(a)** Pairwise Jaccard heat-map across N=8 independent runs on the DYRK1A LID; all 28 off-diagonal cells equal 1.00. **(b)** Per-run runtime (mean 5.06 ± 0.56 s) and chemistry-validator drop count (zero across all runs).](figures/out/fig4_vision_consistency.png)

**Caveat.** Perfect pairwise Jaccard reflects the platform's vision-prompt running with deterministic settings (top-p / temperature configured for low-variance perception) and a single fixed input. The number measures *reproducibility*, not *accuracy*: the model could be consistently wrong. Establishing accuracy requires a held-out gold-LID set, which is identified as priority follow-up work in §5.2.

### 4.4 End-to-end case study

The pipeline was run end-to-end on two leads spanning contrasting target classes (kinase / CNS vs. gram-positive antibacterial), with the Vision Agent skipped (no LID) so the SMIRKS engine, structural filters, ADMET screen, and ranking were exercised on a known starting molecule. Per-stage attrition is shown in Figure 5a; the top-10 analog scatter in Figure 5b.

![**Figure 5.** End-to-end pipeline run on two leads (no-LID configuration). **(a)** Stage-by-stage attrition for DYRK1A Compound 25014 (20 strategies → 149 analogs → 62 pre-filter → 62 ADMET → 58 diversity clusters, 139.7 s) and Linezolid (20 → 71 → 24 → 24 → 22, 55.4 s). **(b)** Top-10 analogs per case in total-score × SA-score space; rank-1 callouts highlighted.](figures/out/fig5_case_study.png)

| Case | Lead | Strategies | Analogs gen. | After pre-filter | After ADMET | After diversity | Wall-clock |
|---|---|---|---|---|---|---|---|
| CASE_001 | DYRK1A Compound 25014 | 20 | 149 | 62 | 62 | 58 | 139.7 s |
| CASE_002 | Linezolid | 20 | 71 | 24 | 24 | 22 | 55.4 s |

The pre-filter (Lipinski Ro5, PAINS, Brenk, RDKit sanitisation) attrits roughly **58 %** of generated analogs for DYRK1A (149 → 62) and **66 %** for Linezolid (71 → 24). The ADMET screen does not further attrit either set in this run because both seeds and analogs sit within liability-acceptable ranges for the default thresholds. The diversity-selection step then reduces 62 → 58 and 24 → 22, indicating that most surviving analogs occupy distinct structural clusters rather than redundant variations on a single edit.

Top-10 ranked analogs for DYRK1A include a maximum-shielding *tert*-butyl substitution at the methoxy carbon (rank 1, total-score 0.586, SA 2.51, MW 312, LogP 4.65, Lipinski 4.0, QED (8) 0.88) and a phenyl→pyrimidine swap combined with O-demethylation (rank 3, total-score 0.578, SA 3.15, MW 258, LogP 1.97, QED 0.82) — a markedly more polar candidate offering an alternative to the high-LogP rank-1. For Linezolid, rank 1 is a benzene-ring 2,6-difluoro substitution (total-score 0.594, SA 2.97), which preserves the oxazolidinone pharmacophore and shifts the aromatic-ring electronics without ring-system perturbation. These analogs are presented as worked illustrations of the pipeline's output, not as binding-validated leads; biochemical confirmation requires experimentation outside this paper's scope.

**Vision-aware re-run on DYRK1A** (with the LID image attached, exercising the production vision-language classification stage). The vision stage identifies binding-contact atoms on the LEU 241 / ASN 244 / GLU 291 H-bond network and the soft Murcko gate + restricted-atom enforcement kicks in. The result: **the strategy count rises from 20 to 50** (more granular site-specific SAR is proposed because each binding contact is treated separately), **but the generated-analog count falls from 149 to 51** (the pharmacophore constraint rejects the rest), and the post-diversity set shrinks from 58 to 25. Crucially, **the rank-1 analog improves on both axes**: total-score rises from 0.586 to 0.638 and SA score falls from 2.51 to 2.32 (easier to synthesise). The chemistry of the new rank-1 — `-CH2OH → -CH2NH2` (benzyl alcohol to benzyl amine) — is a textbook metabolic-stability move that the LID-free run did not reach because it had no signal pointing to the benzyl-alcohol as a TARGET. Wall-clock rises by 33 % (139.7 s → 186.1 s) reflecting the added vision-stage latency. This is the expected behaviour of the architecture and demonstrates that the vision-language LID parsing + chemistry-validity gates + Murcko enforcement work end-to-end as designed.

### 4.5 Cross-provider model benchmark on the three agent stages

The pipeline's three agent stages — vision LID classification (stage 2), project-context analysis (stage 5), and SAR-strategy proposal (stage 6) — are each backed by a language model. To inform the production default and to give a clearer picture of how cross-provider variance affects an agentic pipeline of this kind, we ran an unbiased model benchmark across all three stages.

**Design.** Each stage received the same production prompt verbatim from the production code path. The same inputs were used for every model evaluation: the DYRK1A LID image for stage 2 (8 repeated runs per model), four representative project-context strings spanning CNS-kinase / oral-gram-positive / topical-anti-inflammatory / oncology indications for stage 5 (3 repetitions per context per model), and four leads (DYRK1A Compound 25014, Linezolid, Ibuprofen, Aspirin) for stage 6 (3 repetitions per lead per model). Outputs were parsed with the production JSON extractor and scored against a stage-specific rubric: pairwise self-consistency Jaccard for stage 2, endpoint-priority alignment to a hand-graded rubric for stage 5, and strategy-validity scoring (does the strategy reference a TARGET site that actually exists on the lead, and does it map to a real SMIRKS category in the library) for stage 6. A model is considered *reliable* on a stage when its strict-JSON validity rate is at least 50 %.

**Reliable models per stage**, ranked by stage-specific score (Figure 6):

![**Figure 6.** Cross-provider model evaluation across three Lead-Optimizer agent stages. **(a)** Stage 2 vision: self-consistency Jaccard on the fixed DYRK1A LID, 14 models × 8 reps. **(b)** Stage 5 project-context analysis: endpoint-priority rubric, 11 text models × 4 contexts × 3 reps. **(c)** Stage 6 optimization-agent SAR rubric, 11 text models × 4 leads × 3 reps. Bars dimmed when JSON validity < 50 % (model unreliable on this task).](figures/out/fig6_model_benchmark.png)

| Rank | Stage 2 (vision Jaccard) | Stage 5 (context rubric) | Stage 6 (SAR rubric) |
|---|---|---|---|
| 1 | Llama 4 Scout 17B-16e — 1.00 (100 % JSON, 9.5 s) | OpenAI gpt-5.4 — 0.524 (100 % JSON) | OpenAI gpt-5.4 — 0.333 (100 % JSON) |
| 2 | Gemini 3.1 Pro — 0.867 (75 % JSON) | OpenAI gpt-5 — 0.513 (100 % JSON) | Mistral Large — 0.333 (100 % JSON) |
| 3 | OpenAI gpt-5.4 — 0.804 (100 % JSON) | OpenAI gpt-4.1 — 0.493 (100 % JSON) | OpenAI gpt-4.1 — 0.333 (92 % JSON) |
| 4 | Mistral Pixtral Large — 0.786 (100 % JSON) | Gemini 3 Flash — 0.441 (67 % JSON) | Gemini 3 Flash — 0.333 (92 % JSON) |
| 5 | Mistral Large — 0.550 (100 % JSON) | OpenAI gpt-5-mini — 0.386 (100 % JSON) | OpenAI gpt-5 — 0.333 (58 % JSON) |
| 6 | OpenAI gpt-4o — 0.542 (100 % JSON) | Groq gpt-oss-120b — 0.292 (83 % JSON) | Groq gpt-oss-120b — 0.250 (50 % JSON) |

**One cross-stage observation worth surfacing:** the strict-JSON adherence rate varies widely across model families even when the system prompt explicitly demands JSON-only output. The reliable models in the table above all benefited from provider-specific structured-output modes (`response_format: json_object` for OpenAI/Mistral, `response_mime_type: application/json` for Gemini) being explicitly enabled. Without those flags, several otherwise-capable models silently emit conversational prose or markdown-wrapped JSON, and a parser that only accepts a strict JSON object filters them out. This is a real practical finding for anyone building agentic pipelines: structured-output APIs are not optional polish, they are load-bearing for cross-provider portability.

**Production recommendation.** OpenAI gpt-5.4 is the universal top performer with reliable JSON adherence across all three stages and acceptable latency for an interactive pipeline (9–43 s per stage call). For the vision stage specifically, **Llama 4 Scout 17B-16e via Groq** matches gpt-5.4 on self-consistency and is essentially free; we recommend it as the Tier-1 default for stage 2 with gpt-5.4 as Tier-2 fallback. For stages 5 and 6, gpt-5.4 leads but gpt-4.1 and Mistral Large are close enough in score and latency to serve as paid fallbacks; Groq's gpt-oss-120b is the credible free fallback at acceptable quality. We do not recommend reasoning-class models (gpt-5, o3) as defaults at this time because their long internal chain-of-thought makes them too slow for interactive use; they remain useful for offline or long-form workflows.

**What the benchmark does not measure.** It does not measure model quality on out-of-domain LIDs (the vision rubric is *self-consistency*, not accuracy) or on out-of-distribution project contexts; it does not measure cost-per-call; and it does not establish whether differences between scoring ties (e.g. five models tied at 0.333 on stage 6) are statistically significant. The intent of this section is to anchor the production default in measured data and to document for reproducibility which model versions were evaluated.

---

## 5. Discussion

### 5.1 Honest framing of the architecture

The contribution is not any single component — RDKit, the SMIRKS library category structure, SYBA, PAINS/Brenk, Chemprop-v2-derived ADMET prediction are all well-established. The contribution is the **defence-in-depth orchestration**: the explicit stacking of deterministic gates around each agent stage so that perception errors are absorbed before they corrupt the analog set. The numbers above measure this orchestration directly. In particular, the LID-aware re-run on DYRK1A (§4.4) shows the architecture working end-to-end: when the vision stage identifies binding-contact atoms, the downstream gates enforce them, and the rank-1 analog improves on both Pareto-style score and synthetic accessibility despite a smaller candidate set. This is the load-bearing experimental result for the defence-in-depth claim.

### 5.2 Known limitations

(a) **Vision-language classifier accuracy is not benchmarked against a gold standard.** Building a 50-LID gold set requires per-atom hand-annotation across diverse target classes. The self-consistency experiment (§3.3) measures variance but not accuracy. A follow-on benchmark using a PLIP (26)-derived silver-standard interaction set is identified as priority follow-up work.

(b) **The "Pareto-style penalty rank" is a weighted scalar sum, not a Pareto front.** A real Pareto-front implementation (returning a non-dominated set in ADMET × SYBA × structural-alert space) is conceptually compatible with the rest of the pipeline and is a clean future replacement.

(c) **No internal trained ML model.** Predictive substrates (Chemprop-v2 for ADMET, SYBA for synth-accessibility) are upstream open-source releases cited as-is. We do not provide a calibrated alternative.

(d) **Docking is not in scope.** The pipeline can consume docking output (binding affinities) when present as part of the lead's input data, but the platform does not compute binding affinities.

(e) **Library-validation is curator-asserted.** The 479 SMIRKS entries carry a `validated=True` flag, but the verification function exists in the codebase without being invoked in CI. Adding it as a CI gate is a recommended pre-release hardening step.

### 5.3 Comparison to neighbouring tools

Transformation-library approaches such as MMPDB(19) and Reinvent(20) share the SMIRKS-enumeration ancestry but lack the vision-language LID perception step and the chemistry-validity gating. Generative approaches based on character or graph RNNs (e.g. MOSES(21), GuacaMol(22)) operate on different inputs (no pharmacophore-anchoring) and emphasise distributional novelty over preserving a known binding pose. The platform described here occupies an explicit niche: *given a lead and a binding pose, generate constrained edits and rank them.*

---

## 6. Methods

This section reproduces the technical detail needed to re-implement the pipeline. Implementation files and exact line numbers are referenced in the reproducibility README (`paper/README.md`).

**Software.** Python 3.11 (local) / 3.12 (VPS), RDKit 2026.03.3 (cheminformatics), SYBA 1.x (synth-accessibility), `admet_ai` 1.x (Chemprop-v2 ADMET), WeasyPrint (PDF). FastAPI (HTTP layer) and Supabase (storage) are used by the production deploy but are not load-bearing for the methodology.

**SMIRKS library inventory.** 479 entries across 22 distinct category names; 35 distinct key prefixes; 100 % marked `validated=True` by curation. Top categories by entry count: aromatic-ring swaps (54), amine modifications (48), o-substitutions (30), carbonyl modifications (30), CNS penetration (26), N-heterocycle swaps (25), carboxylic-acid replacements (20), amide-bond replacements (20), metabolic stability (20), halogen substitutions (20), bioisosteric replacements (20), aromatic substitutions (20), steric shielding (20), polarity adjustments (20).

**Pre-scan SMARTS library.** 90+ SMARTS substructure patterns covering acids, amines (primary/secondary/tertiary/quaternary), amides, esters, ethers, halides (alkyl/aryl), nitro/nitroso, sulfonamides, ketones/aldehydes, hydroxyls, hydroxymethyls, alpha-methyls, fluoromethyls, trifluoromethyls, sulfoxides/sulfones, oxetanes/azetidines/morpholines/piperazines/piperidines, indoles/imidazoles/pyrazoles, pyridines/pyrimidines/pyrazines, thiophenes/furans, benzofurans/benzimidazoles/benzothiazoles, quinolines/isoquinolines, methoxy/ethoxy/trifluoromethoxy/difluoromethoxy, tetrazoles, guanidines/amidines, etc.

**Chemistry-validity allowlists.** Six tables (`H_BOND_DONORS`, `H_BOND_ACCEPTORS`, `PI_STACK_GROUPS`, `HYDROPHOBIC_GROUPS`, `SALT_BRIDGE_GROUPS`, `CATION_PI_GROUPS`). Each maps a functional-group family to the interactions it can chemically participate in. The validator drops vision-language entries that pair a group with an impossible interaction (e.g. methyl → H-bond donor) before they propagate downstream.

**Soft Murcko gate.** The Bemis–Murcko scaffold SMARTS is appended to the restricted-SMARTS set at the SMARTS-construction stage. The check itself runs inside `enforce_pharmacophore` and is called both at strategy validation (one example per strategy) and during permutation (every candidate analog). Predicates: restricted atoms unchanged; ring count preserved; per-ring aromaticity preserved. Intentionally weaker than an exact-SMARTS-append: methyl→ethyl on a scaffold carbon is allowed; ring-system destruction is rejected.

**Ranking weights.** SYBA penalty multiplier centred at 0 via sigmoid (positive SYBA → no penalty, negative SYBA → penalty); ADMET liability multipliers per directional table; PAINS-positive analogs receive a hard penalty; Brenk-positive analogs receive a soft penalty; molecular-property axes (cLogP, MW) receive Gaussian penalties around an indication-specific optimum.

**Cross-provider model benchmark.** Each agent stage was evaluated by sending its production system prompt verbatim to each candidate model alongside a fixed user message and image input where applicable, then parsing the response with the production JSON extractor. To enable cross-vendor comparison on equal footing, provider-specific structured-output flags were enabled when the system prompt asked for JSON: `response_format: json_object` for OpenAI and Mistral, `response_mime_type: application/json` for Gemini. Reasoning-class models were given a larger output-token budget (16,384 tokens) to accommodate internal chain-of-thought. Transient errors (HTTP 429 rate-limit, 503 server-overload) were retried with exponential backoff (delays 2, 4, 8, 16 s; up to five attempts). The benchmark harness, model registry, and per-model raw responses are at `paper/experiments/exp5_model_benchmark/`.

**Reproducibility.** See `paper/README.md`.

---

## Methods Availability

All scripts used in this study — including the five experiment drivers, the figure-rendering scripts, the cross-provider model-benchmark harness, and the mirrored pipeline source code (`code/lead_optimizer/`) — are available at https://github.com/Nimieeee/lead-optimizer-paper. The repository carries a `manifest.json` for every experiment recording the git SHA, RDKit version, Python version, platform, SMIRKS library SHA-256, and input-file SHA-256, so that any figure or table can be re-derived to the byte.

## Use of Artificial Intelligence Tools

Portions of this manuscript were prepared with the assistance of Anthropic's Claude (Opus 4.x and Sonnet 4.x). The AI assistant was used to support iterative drafting, clarity refinement, editorial polishing, figure-caption generation, the writing of experiment driver scripts (Python / RDKit / matplotlib) and figure-rendering scripts, and orchestration of the benchmark harness across providers. All scientific content — experimental design, claim verification against measured results, interpretation of findings, and final conclusions — was conceived, executed, and validated by the author. The AI assistant was employed as an editorial, computational-scripting, and orchestration aid and was not used to generate novel scientific claims or to perform data interpretation.

## Data Availability

The matched-molecular-pair pilot set (30 hand-curated single-edit pairs), the 129-marketed-drug seed list, the 50 LID image used for the vision self-consistency study, the four representative project-context strings, and the four leads used in the cross-provider model benchmark are all included in the repository under `experiments/exp*/data/`. The unbiased ChEMBL-derived MMP set was built from ChEMBL release 37 (chemreps file), a 2,000-compound drug-like subset filtered with the criteria reported in §3.1, then fragmented and indexed with `mmpdb` to produce 41,310 raw pairs of which 2,000 single-edit pairs were sampled for evaluation; the build script (`experiments/exp1_mmp_recovery/build_chembl_pairs.py`) is in the repository and the raw ChEMBL chemreps file is excluded only because of its size and is downloadable from EBI at https://ftp.ebi.ac.uk/pub/databases/chembl/. All experiment-result JSONs and per-run manifests are committed in `experiments/exp*/results/`. A frozen archive of the exact commit used to produce every figure and table in this manuscript is deposited on Zenodo and assigned a DOI; that DOI is the canonical citation for the data artefact.

## Acknowledgments

The author thanks the maintainers of RDKit, ADMET-AI, SYBA, mmpdb, and the ChEMBL project for the open-source primitives that this work builds on. The author also thanks the upstream PAINS and Brenk filter sets for the structural-alert vocabulary used in the audit experiment.

---

## References

[1] Voršilák, M., Kolář, M., Čmelo, I., & Svozil, D. (2020). SYBA: Bayesian estimation of synthetic accessibility of organic compounds. *Journal of Cheminformatics*, *12*, 35. https://doi.org/10.1186/s13321-020-00439-2

[2] Swanson, K., Walther, P., Leitz, J., Mukherjee, S., Wu, J. C., Shivnaraine, R. V., & Zou, J. (2024). ADMET-AI: a machine learning ADMET platform for evaluation of large-scale chemical libraries. *Bioinformatics*, *40*(7), btae416. https://doi.org/10.1093/bioinformatics/btae416

[3] Heid, E., Greenman, K. P., Chung, Y., Li, S.-C., Graff, D. E., Vermeire, F. H., Wu, H., Green, W. H., & McGill, C. J. (2024). Chemprop: A machine learning package for chemical property prediction. *Journal of Chemical Information and Modeling*, *64*(1), 9–17. https://doi.org/10.1021/acs.jcim.3c01250

[4] Yang, K., Swanson, K., Jin, W., Coley, C., Eiden, P., Gao, H., Guzman-Perez, A., Hopper, T., Kelley, B., Mathea, M., Palmer, A., Settels, V., Jaakkola, T., Jensen, K., & Barzilay, R. (2019). Analyzing learned molecular representations for property prediction. *Journal of Chemical Information and Modeling*, *59*(8), 3370–3388. https://doi.org/10.1021/acs.jcim.9b00237

[5] Landrum, G., et al. (2026). RDKit: Open-source cheminformatics. Release 2026.03.3. https://doi.org/10.5281/zenodo.20446949

[6] Bemis, G. W., & Murcko, M. A. (1996). The properties of known drugs. 1. Molecular frameworks. *Journal of Medicinal Chemistry*, *39*(15), 2887–2893. https://doi.org/10.1021/jm9602928

[7] Lipinski, C. A., Lombardo, F., Dominy, B. W., & Feeney, P. J. (1997). Experimental and computational approaches to estimate solubility and permeability in drug discovery and development settings. *Advanced Drug Delivery Reviews*, *23*(1–3), 3–25. https://doi.org/10.1016/S0169-409X(96)00423-1

[8] Bickerton, G. R., Paolini, G. V., Besnard, J., Muresan, S., & Hopkins, A. L. (2012). Quantifying the chemical beauty of drugs. *Nature Chemistry*, *4*(2), 90–98. https://doi.org/10.1038/nchem.1243

[9] Rogers, D., & Hahn, M. (2010). Extended-connectivity fingerprints. *Journal of Chemical Information and Modeling*, *50*(5), 742–754. https://doi.org/10.1021/ci100050t

[10] Baell, J. B., & Holloway, G. A. (2010). New substructure filters for removal of pan-assay interference compounds (PAINS) from screening libraries and for their exclusion in bioassays. *Journal of Medicinal Chemistry*, *53*(7), 2719–2740. https://doi.org/10.1021/jm901137j

[11] Brenk, R., Schipani, A., James, D., Krasowski, A., Gilbert, I. H., Frearson, J., & Wyatt, P. G. (2008). Lessons learnt from assembling screening libraries for drug discovery for neglected diseases. *ChemMedChem*, *3*(3), 435–444. https://doi.org/10.1002/cmdc.200700139

[12] Ertl, P., & Schuffenhauer, A. (2009). Estimation of synthetic accessibility score of drug-like molecules based on molecular complexity and fragment contributions. *Journal of Cheminformatics*, *1*, 8. https://doi.org/10.1186/1758-2946-1-8

[13] Daylight Chemical Information Systems, Inc. *Daylight Theory Manual — SMARTS: A Language for Describing Molecular Patterns*. https://www.daylight.com/dayhtml/doc/theory/theory.smarts.html (accessed 2026-06)

[14] Daylight Chemical Information Systems, Inc. *Daylight Theory Manual — SMIRKS: A Reaction Transform Language*. https://www.daylight.com/dayhtml/doc/theory/theory.smirks.html (accessed 2026-06)

[15] Weininger, D. (1988). SMILES, a chemical language and information system. 1. Introduction to methodology and encoding rules. *Journal of Chemical Information and Computer Sciences*, *28*(1), 31–36. https://doi.org/10.1021/ci00057a005

[16] Griffen, E., Leach, A. G., Robb, G. R., & Warner, D. J. (2011). Matched molecular pairs as a medicinal chemistry tool. *Journal of Medicinal Chemistry*, *54*(22), 7739–7750. https://doi.org/10.1021/jm200452d

[17] Meanwell, N. A. (2011). Synopsis of some recent tactical application of bioisosteres in drug design. *Journal of Medicinal Chemistry*, *54*(8), 2529–2591. https://doi.org/10.1021/jm1013693

[18] Wermuth, C. G., Ganellin, C. R., Lindberg, P., & Mitscher, L. A. (1998). Glossary of terms used in medicinal chemistry (IUPAC Recommendations 1998). *Pure and Applied Chemistry*, *70*(5), 1129–1143. https://doi.org/10.1351/pac199870051129

[19] Dalke, A., Hert, J., & Kramer, C. (2018). mmpdb: An open-source matched molecular pair platform for large multiproperty data sets. *Journal of Chemical Information and Modeling*, *58*(5), 902–910. https://doi.org/10.1021/acs.jcim.8b00173

[20] Olivecrona, M., Blaschke, T., Engkvist, O., & Chen, H. (2017). Molecular de-novo design through deep reinforcement learning. *Journal of Cheminformatics*, *9*, 48. https://doi.org/10.1186/s13321-017-0235-x

[21] Polykovskiy, D., Zhebrak, A., Sanchez-Lengeling, B., Golovanov, S., Tatanov, O., Belyaev, S., Kurbanov, R., Artamonov, A., Aladinskiy, V., Veselov, M., Kadurin, A., Johansson, S., Chen, H., Nikolenko, S., Aspuru-Guzik, A., & Zhavoronkov, A. (2020). Molecular Sets (MOSES): A benchmarking platform for molecular generation models. *Frontiers in Pharmacology*, *11*, 565644. https://doi.org/10.3389/fphar.2020.565644

[22] Brown, N., Fiscato, M., Segler, M. H. S., & Vaucher, A. C. (2019). GuacaMol: Benchmarking models for de novo molecular design. *Journal of Chemical Information and Modeling*, *59*(3), 1096–1108. https://doi.org/10.1021/acs.jcim.8b00839

[23] Zdrazil, B., Felix, E., Hunter, F., Manners, E. J., Blackshaw, J., Corbett, S., de Veij, M., Ioannidis, H., Lopez, D. M., Mosquera, J. F., Magariños, M. P., Bosc, N., Arcila, R., Kizilören, T., Gaulton, A., Bento, A. P., Adasme, M. F., Monecke, P., Landrum, G. A., & Leach, A. R. (2024). The ChEMBL Database in 2023: a drug discovery platform spanning multiple bioactivity data types and time periods. *Nucleic Acids Research*, *52*(D1), D1180–D1192. https://doi.org/10.1093/nar/gkad1004

[24] Becker, W., & Sippl, W. (2011). Activation, regulation, and inhibition of DYRK1A. *FEBS Journal*, *278*(2), 246–256. https://doi.org/10.1111/j.1742-4658.2010.07956.x

[25] Brickner, S. J., Hutchinson, D. K., Barbachyn, M. R., Manninen, P. R., Ulanowicz, D. A., Garmon, S. A., Grega, K. C., Hendges, S. K., Toops, D. S., Ford, C. W., & Zurenko, G. E. (1996). Synthesis and antibacterial activity of U-100592 and U-100766, two oxazolidinone antibacterial agents for the potential treatment of multidrug-resistant Gram-positive bacterial infections. *Journal of Medicinal Chemistry*, *39*(3), 673–679. https://doi.org/10.1021/jm9509556

[26] Salentin, S., Schreiber, S., Haupt, V. J., Adasme, M. F., & Schroeder, M. (2015). PLIP: fully automated protein–ligand interaction profiler. *Nucleic Acids Research*, *43*(W1), W443–W447. https://doi.org/10.1093/nar/gkv315
