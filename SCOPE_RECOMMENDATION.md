# Phase 2 — Preprint scope recommendation

**Decision pending — see §5. Read this, then tell me to proceed (or redirect).**

---

## TL;DR

**Recommend Option B (focused paper) with the Lead Optimization Workbench as the primary contribution.** ADMET serves as a screening stage inside the Lead Optimizer story (cited honestly as upstream `admet_ai` / Chemprop v2). The whole-platform paper (Option A) is a stronger second submission, written *after* the focused paper establishes the methodological credibility.

The reason isn't a guess — it's what the inventory in `CODEBASE_NOTES.md` actually permits. Below: each option scored on novelty, completeness, validatability, with the trade-offs called out plainly.

---

## 1 — The two options, scored

### Option A — Whole-platform paper
*"Benchside: an integrated agentic platform for computer-aided drug discovery"*

| Axis | Score | Reasoning |
|---|---|---|
| Novelty | **Medium** | The integration is novel — agentic CADD as a vertically-integrated web platform with deterministic gate-shortlisting, vision-agent ligand interaction classification, multi-node deep research, multi-provider LLM routing. But most substrates are off-the-shelf: `admet_ai` (Chemprop v2, Swanson 2024), RDKit, SYBA, Mistral embeddings, PubMed/Serper. The novelty is in the orchestration, not the ML. |
| Completeness | **High** | Production-deployed on a Contabo VPS + Vercel. 39 services in the container, ~280 regression tests in CI, ~748 total `def test_` definitions. The full stack runs and is used. |
| Validatability | **Low to medium** | The platform has **no internal benchmarks**: zero TDC/MoleculeNet/ChEMBL imports, no held-out evaluation set, no comparison to baselines for *any* component. Every quantitative claim in a whole-platform paper would have to be built from scratch in Phase 3. To validate "the platform works," you would need to benchmark each component independently, which is at least 4× the work of validating one component. |
| Venue fit | Software-X, JOSS, BMC Bioinformatics methods | Not a fit for top cheminformatics journals on first submission — peer reviewers in those venues will ask for component-level benchmarks, and an integration paper without those reads as a marketing piece. |

**Honest risk:** a whole-platform paper reads like a system description without an experimental backbone. The most likely outcome at a serious cheminformatics venue is "interesting platform, but where are the benchmarks?" Without §3 below built out first, the reviewers will be right.

### Option B — Focused paper, Lead Optimization Workbench
*"A vision-language agentic pipeline for lead optimization: per-instance SMARTS classification, soft Murcko-scaffold preservation, and SYBA-anchored ranking"*

| Axis | Score | Reasoning |
|---|---|---|
| Novelty | **High** | The Vision-Agent → per-instance SMARTS (`phenyl_left` vs `phenyl_right` via RDKit 2D coordinates) → chemistry-validity validator → soft Murcko ring-topology gate → SYBA-anchored ranking pipeline does not exactly exist in the published literature. Closest neighbours are MMPDB-style transformation enumeration, Reinvent reinforcement-learning generators, and matched-pair-aware QSAR. None combine: (a) vision-LM ligand-interaction-diagram parsing, (b) per-instance disambiguation from 2D coords, (c) chemistry-validity allowlists that drop hallucinated classifications, (d) soft topology-preserving scaffold gate, (e) signed SYBA score as the ranking-penalty signal. **This is the strongest novelty story in the repo.** |
| Completeness | **High** | All 12 stages of the pipeline are wired (Pre-scan → Vision → SMARTS → ADMET → Context → Optimization → Validate → Permutation → Pre-filter → ADMET screen → SYBA → Ranking → Report). 38 unit tests cover schema, multi-residue handling, atom-indices, Murcko detection, scaffold-SMARTS construction, chemistry validator, label resolution. Production deploy works. Two limitations to surface: (i) `STRUCTURAL_CORE` field still exists despite removal from the prompt (back-compat merge path), (ii) the SMIRKS library's `validated=True` flag is curation-asserted; the `validate_entire_library()` function exists at `smirks_library.py:6005` but is not invoked in CI — adding it as a regression gate is a low-cost paper-readiness step. |
| Validatability | **High** | Four credible experiments are feasible in 2–4 weeks: (1) **MMP-recovery rate** on a public ChEMBL-derived matched-molecular-pair set — does the permutation engine propose the empirically-observed improving transformation? (2) **PAINS / Brenk / structural-alert audit** of generated analogs vs Reinvent or MOSES baseline on the same lead. (3) **Murcko-scaffold preservation rate** across diverse scaffolds (this is *the* novel claim: soft gate preserves scaffold while allowing meaningful edits). (4) **Vision-Agent accuracy** on a held-out set of 50 LIDs hand-labelled against PDB/literature. Each is concrete, reproducible, and resists hand-waving. |
| Venue fit | JCIM, J. Med. Chem., RSC Digital Discovery, Bioinformatics, ChemRxiv working paper | Strong fit. The methods section has substance, the validation section has concrete baselines, the case study (DYRK1A or PBP2a) gives a narrative. |

**Honest risk:** vision-model accuracy on LIDs is the load-bearing claim and could come in lower than the platform's marketing pitch. The fix is to present the chemistry validator + Murcko gate + SMIRKS library as **defence-in-depth that prevents a wrong vision call from corrupting the output**. That framing turns a weakness into the paper's actual contribution.

---

## 2 — The sub-options I considered for Option B and rejected

### B2 — ADMET engine alone
**Rejected.** The ML is upstream `admet_ai` (Chemprop v2, Swanson et al. 2024). Benchside contributes orchestration, directional scoring, SVG rendering, and exports — useful, but not paper-worthy as a standalone methodological contribution. A TDC benchmark would only re-confirm upstream numbers. The directional-scoring layer (Rule 6) is a single-figure contribution at best.

### B3 — Table Intelligence
**Rejected as primary.** Genuinely interesting (deterministic Python gates + LLM narration, audit/replay with RLS), and it could be a future paper on reproducible shortlisting for medicinal chemistry. But the audience is narrow, the chemistry novelty is lower than Lead Optimizer, and the validation story (decision agreement on repeat-runs, comparison to LLM-only baseline) is interesting but less compelling than MMP recovery. **Recommend keeping it in reserve for Paper 2 or 3.**

### B4 — Deep Research pipeline
**Rejected.** Multiple groups have built similar 4-node agentic literature systems (Elicit, Consensus, OpenScholar, STORM). The Benchside deep-research backend invokes only PubMed + Serper Google Scholar, the EvidenceValidator is dead code, and there is no citation-faithfulness measurement in the current repo. To make this paper credible, **citation faithfulness would have to be built and run on a sample of 50–100 reports** — and even then the contribution feels incremental against the published field. The work is valuable; the paper would have to wait until the validation harness exists.

---

## 3 — What the focused Lead-Optimizer paper would actually claim

This is what I'd commit to writing if you greenlight Option B:

### Methodological contributions (the novelty pitch)
1. **Vision-language ligand-interaction-diagram parsing** with per-instance disambiguation via 2D coordinates (avoids the "two phenyls collapse to one SMARTS" failure mode).
2. **Chemistry-validity allowlists** (`chemistry_validator.py`) that drop physically-impossible classifications from the vision-model output (e.g. methyl as H-bond donor, methoxy as donor). Defence-in-depth against vision-model perception failures.
3. **Soft Murcko-scaffold ring-topology gate** that allows substituent edits on scaffold carbons while rejecting ring-system destruction. Replaces the brittle hard-SMARTS-append approach.
4. **SYBA-anchored Pareto-style penalty ranking** that uses signed SYBA score as the primary synth-accessibility signal (Voršilák 2020), with directional ADMET multipliers.
5. **A two-category (RESTRICTED vs TARGET) site classification** that prevents permutation from attacking pharmacophore atoms while keeping the rest of the molecule editable. The "fundamental error" the user surfaced (STRUCTURAL_CORE category was redundant) becomes the paper's clarifying contribution.

### Validation we'd run in Phase 3
1. **MMP-recovery rate** on ChEMBL MMP pairs — how often does the permutation propose the empirically-observed improving transformation, top-1 and top-10?
2. **Scaffold preservation** on a diverse set (250 leads spanning kinase, GPCR, protease, ion channel) — fraction of generated analogs that preserve Bemis-Murcko scaffold vs Reinvent baseline.
3. **Structural-alert rate** (PAINS, Brenk) on the same 250-lead set vs Reinvent and MOSES baselines.
4. **Vision-Agent accuracy** on a held-out set of 50 LIDs with manually-labelled restricted/target atoms (gold set built from PDB ligand–protein structures + literature).
5. **End-to-end case study**: a single target (DYRK1A or PBP2a per user precedent) with full pipeline trace — number of analogs, SYBA distribution, ADMET-pass rate, top-10 candidates, time-to-result.

### What we'd honestly *not* claim
- Will not claim trained ML models (we use Chemprop v2 / SYBA / RDKit; cite them).
- Will not claim docking (none in repo).
- Will not claim NAPLEX accuracy (none measured; will not appear in this paper).
- Will not claim citation-faithfulness numbers (defer to a future deep-research paper).
- Will report the SMIRKS library size honestly: **479 entries across 22 categories**, all marked `validated=True`, with the caveat that validation is curation-asserted, not runtime-gated.
- Will not claim 104 ADMET endpoints — the runtime surfaces ~54 (UI count); code/paper agreement comes first.
- Will not claim DDI accuracy (LLM-driven, not validated).

---

## 4 — What Option A becomes later

Once the focused Lead-Optimizer paper is on ChemRxiv with Tier-1 validation evidence, the whole-platform paper becomes much stronger because:

- It can cite the Lead-Optimizer paper for the workbench evidence.
- ADMET can be benchmarked on TDC (Tier-1 in §7 of `CODEBASE_NOTES.md`).
- Deep Research can be evaluated for citation faithfulness on a small sample.
- Table Intelligence can be evaluated for decision-agreement reproducibility.
- The integration claim becomes "here is a CADD platform whose individual components have been independently validated in [refs]," which is much harder to dismiss.

Likely venue for the whole-platform paper: **Software-X**, **JOSS**, or a **JCIM Application Note**. Or — if the validation evidence is strong enough — a full **JCIM** methods paper framed as "an opinionated end-to-end CADD platform with measured component-level performance."

Sequenced this way, the platform paper benefits from a year of citations and follows in a stronger position. Trying to fit everything into the first paper means each component gets shortchanged.

---

## 5 — The decision I need from you

Pick one:

- **(A) Whole platform first.** I'll draft the manuscript outline accordingly and lay out Phase 3 with all four components needing independent validation in parallel. Honest assessment: this is the riskier path because validation breadth is hard, and reviewers will probably ask for what the focused paper already delivers.
- **(B) Lead Optimizer first.** *Recommended.* I'll fix the SMIRKS-library size discrepancy (167 vs 479 in code AND prompt) as a prerequisite, then move to Phase 3 with the four experiments listed in §3 above. Optionally, retain ADMET as the "screening stage" framed honestly (upstream `admet_ai`).
- **(C) Something different.** Tell me what — e.g. Table Intelligence as primary, or a different case-study target, or a different validation set. I'll re-plan accordingly.

**I will not start drafting the manuscript until you decide.** When you do, I'll move to Phase 3 (validation experiments → real numbers → figures) and only then Phase 5 (drafting the actual paper).

**One housekeeping item before any decision:** the leaked SMTP credentials in `backend/ecosystem.config.js:9-11` should be rotated before any code release. That's separate from the paper task but it's a prerequisite for the Phase 6 Zenodo archive — flagging now so it's not a surprise later.
