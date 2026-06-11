# Benchside — Codebase inventory for preprint planning

**Date of inventory:** 2026-06-10
**Inventory method:** Five parallel mapping agents read code (not docs) and wrote component-level notes under `paper/notes/0[1-5]_*.md`. This file is the synthesis. Every claim below is traceable to a file:line in the detail notes.

**Tone:** ruthlessly honest. Where the code disagrees with `CLAUDE.md`, `README.md`, or in-file docstrings, the **code wins** and the docs are flagged as drift. The goal is a preprint that survives peer review; underclaim is safer than overclaim.

> **CORRECTION 2026-06-10 (later):** The original Phase 1 inventory claimed the SMIRKS library
> was 167 entries across 17 categories (vs the docs' "479 across 22+"). This was a regex bug:
> the count pattern `^\s*"[A-Z_]+_[0-9]+":` required an underscore between letters and digits,
> but the library has 312 entries whose keys use the format `POLA019` / `NHEX001` (no underscore).
> The authoritative count, verified by Python import, is **479 entries across 22 distinct
> category-field values and 35 distinct key prefixes**, with all 479 marked `validated=True`.
> CLAUDE.md and the in-code prompts were correct. The drift table in §6 has been updated;
> any number you saw in an earlier version of this file should be re-read.

---

## 0 — Executive summary

Benchside is a working integrated drug-discovery web platform: ADMET screening, agentic lead-optimization, deep-research literature pipeline, deterministic gate-based candidate shortlisting, retrieval-augmented chat, and lab/studio UIs. The components run in production today (`pharmgpt-api` on Contabo VPS + Vercel frontend).

What the platform **is** and **is not**, calibrated against actual code:

| Capability | Status | Substrate |
|---|---|---|
| ADMET prediction | Working orchestration | Thin wrapper around **upstream `admet_ai` PyPI package (Chemprop v2, Swanson et al. 2024)** — no Benchside-trained ML model |
| Synth-accessibility | Working — SYBA primary | Voršilák et al. 2020 SYBA + Ertl 2009 SAScore fallback. GASA checkpoint present but inert (`dgl` not installed) |
| Lead optimization | 12-stage agentic pipeline, fully wired | Vision Agent + RDKit + per-instance SMARTS + soft Murcko gate + chemistry validator + **479-entry SMIRKS library across 22 categories**, all marked validated + Pareto-named weighted scalar ranking |
| Deep Research | 4-node agentic (planner → researcher → reviewer → writer) | LLM-orchestrated with PubMed E-utilities + Serper Google Scholar only |
| Table Intelligence | 7 deterministic GateSets + audit/replay | Schema detection + intent classification + indication-keyed gates; LLM narrates, never computes |
| LLM routing | Multi-provider with fallback chains | OpenCode Go MiMo / Pollinations / Groq / Mistral. NVIDIA NIM still initialised but dead-letter only. Anthropic-compat lives only in Vision Agent |
| RAG | Mistral embeddings + lexical Jaccard/RRF rerank | No external reranker; citation granularity is filename-only |
| DDI analysis | LLM-driven; NLM RxNav advertised but admitted-discontinued | No DrugBank dump, no PMID-grounded evidence |
| Docking / Schrödinger / MCP | **Not in repo.** Platform reasons over user-uploaded docking output | Hits for "schrodinger/vina/autodock" are column-alias parsers for user CSVs |
| Benchmark / evaluation harnesses | **Not in repo.** Zero TDC/MoleculeNet/ChEMBL imports | The only "benchmarks" are LLM latency/word-count measurements |
| NAPLEX evaluation | **Not in repo.** Zero hits anywhere | A paper claiming NAPLEX accuracy would have to build the harness from scratch |
| Citation faithfulness | **Not measured.** No claim→source verification | `_verify_citation_density()` is a density metric, not faithfulness |
| Test suite | 748 `def test_` across 47 files; ~280 run in regression CI | Component-level coverage strong; no end-to-end integration test of lead-optimization or deep-research pipelines |

The honest summary: **Benchside is a production-grade orchestration layer built on top of well-established ML and cheminformatics substrates (Chemprop v2 ADMET-AI, RDKit, SYBA), with several novel agentic pipelines (Vision-Agent SMARTS classification, deterministic GateSet shortlisting, multi-node deep research). It has no internal ML training, no docking engine, and no published benchmark evaluation as of today. Validation for a preprint must be built in Phase 3.**

---

## 1 — ADMET engine
**Detail:** `paper/notes/01_admet.md`

### What the code actually is
`backend/admet_engine.py` calls `from admet_ai import ADMETModel; _model = ADMETModel(); _model.predict(smiles)`. All ML lives in the upstream **ADMET-AI** package (Chemprop v2 graph neural net, trained by Swanson et al. 2024 on TDC splits). Benchside contributes:

- An HTTP microservice wrapping the predictor (FastAPI on port 7861, separate PM2 process)
- Endpoint orchestration + caching + retries
- DrugBank-percentile → confidence-label mapping (`admet_service.py:54-64`) — the percentile itself is inherited from upstream
- Directional scoring layer (`postprocessing/admet_processor.py`) — Rule 6 in `CLAUDE.md`, locked by 9 unit tests
- SVG structure rendering and PDF/DOCX export with Mermaid + Markdown safety processing

### Concrete numbers
- **54 endpoints actually surfaced** in the UI, across 7 groups (Physicochemical 9, Drug-Likeness 5, Absorption 8, Distribution 3, Metabolism 8, Excretion 3, Toxicity 18 including 12 Tox21 alerts).
- The pydantic response model has `endpoints: int = 104` as a **hardcoded default** — that is where "104 endpoints" comes from in docs. Not a runtime count.
- `LD50_Zhu` is computed and confidence-mapped but **never displayed** (missing from `property_groups`).
- **Latent bug** — Tox21 prefix mismatch: `_generate_ai_interpretation` greps for `Tox21_*`, but ADMET-AI emits `NR-*` / `SR-*`. The AI-interpretation Tox21-alert branch is dead code.

### Synth-accessibility
- **SYBA is the runtime metric.** `synth_accessibility_service.py` orchestrates SYBA → Ertl SAScore → descriptor heuristic in that order.
- `gasa_model/gasa.pth` is a real PyTorch checkpoint but the loader requires `dgl`, which is not installed in the production venv. The "GASA" name persists across four backward-compat aliases but the implementation always falls through to SYBA. Rule 36 is honoured: the API and reports key on `syba_score`.

### Exports
- PDF/DOCX/CSV all surface SYBA primary, SAScore legacy, GASA-style fields fallback-only.
- WeasyPrint asserts were fixed at commit `8b1b554` (single CSS line: `page-break-inside: avoid` on `.analog-card` removed).

### Tests
- **39 tests** in `test_admet_service.py` across 8 classes. All HTTP calls mocked. **Real ADMET-AI engine is never exercised in CI**.
- No tests for `synth_accessibility_service.py`.
- No tests for PDF/DOCX generation.
- 2 tests assert `... or True` and are effectively inert.

### Validation gaps for a paper
- **No TDC benchmark in repo.** No `evaluate.py`, no leaderboard JSON, no held-out comparison. Upstream ADMET-AI's published numbers (AUROC/MAE per task on TDC ADMET Benchmark Group) would have to be cited as-is or independently re-run.
- DrugBank percentile is inherited from upstream — Benchside does not maintain its own reference distribution.
- No internal calibration plot, no reliability diagram, no class-imbalance reporting.

### What's solid / partial / missing
**Solid:** orchestration, directional scoring (Rule 6, tested), SYBA wiring (Rule 36, tested), structure rendering, exports, multi-fallback (local → ADMETlab `wash_molecule` only → RDKit-only).
**Partial:** "ADMETlab 3.0 prediction fallback" — only `wash_molecule()` actually calls `admetmesh.scbdd.com`; prediction fallback chain in `CLAUDE.md` is partially obsolete. UI endpoint count understated. AI-interpretation Tox21 branch is dead.
**Missing:** internal benchmark numbers, calibration evaluation, real-engine integration test, dataset-shift analysis.

---

## 2 — Lead Optimizer
**Detail:** `paper/notes/02_lead_optimizer.md`

### The pipeline (verified against `orchestrator.py`)
Twelve stages, all wired:
**Pre-scan → Vision Agent → SMARTS Builder → ADMET Profile → Context Analysis → Optimization Agent → Validate → Permutation → Pre-filter → ADMET screen → GASA/SYBA → Ranking → Report**

### Vision Agent (the novel piece)
- **Provider chain in code today:** Kimi K2.6 (OpenCode Go OAI-compat with `reasoning_content` fallback) → MiniMax M3 (env-gated, **default disabled**) → Pixtral Large (Mistral) → Groq Scout 17B-16e. The CLAUDE.md row claiming Llama 4 Maverick 17B-128e replaced Scout is **drift** — code still ships Scout (`vision_agent.py:36`).
- Schema: `residues: list[str]`, `interaction_types: list[InteractionType]`, `atom_indices: list[int]` per `FunctionalGroupInteraction`. Multi-residue support verified.
- Two-category classification (RESTRICTED vs TARGET) per the user's correction. `STRUCTURAL_CORE` removal is **partial** — gone from the prompt and JSON schema example, but `VisionAgentOutput.structural_core_groups` field still exists; any payload that comes through it is auto-merged into `target_groups` (`vision_agent.py:526-530`).
- **Chemistry validator** (`chemistry_validator.py`) — allowlist tables for H-bond donors / acceptors / π-stack / hydrophobic / salt-bridge / cation-π. Drops chemically impossible classifications (e.g. methyl as H-bond donor).
- VISIBLE LINE rule (Rule 3a) in the prompt — no inferring contacts from residue type.

### SMARTS builder + scaffold gate
- Per-instance labelling — `phenyl_left`, `phenyl_right`, `aromatic_h_left-top` — derived from RDKit 2D coordinates. Solves the "two phenyl rings collapse to one SMARTS" problem.
- Soft Murcko gate: ring count + aromaticity preservation. Replaces an earlier hard SMARTS append. Allows methyl→ethyl on scaffold carbons while rejecting ring-system destruction.
- `enforce_pharmacophore` rejects analogs that broke a restricted atom.

### SMIRKS library — count verified
- **Authoritative count: 479** entries across 22 distinct `category` field values and 35 distinct key prefixes. Verified by `from app.services.lead_optimizer.smirks_library import SMIRKS_LIBRARY; len(SMIRKS_LIBRARY)` (Python import, not regex). All 479 marked `validated=True`.
- Earlier inventory said 167. That was a regex artifact: the pattern `^\s*"[A-Z_]+_[0-9]+":` required an underscore between the alphabetic prefix and the numeric suffix, but 312 entries use the format `POLA019` / `NHEX001` (no underscore). Mea culpa — preserved here so the audit trail is visible.
- CLAUDE.md row dated 2026-04-24 claims "344 → 479".
- The live `OPTIMIZATION_AGENT_SYSTEM_PROMPT` (`prompts.py:199`) tells the LLM "479 validated SMIRKS entries".
- The LLM is being prompted with a count ~3× the real library. This needs to be fixed in code AND in the paper.
- `validate_entire_library()` exists at `smirks_library.py:6005` but **is never called** from any code path. "All RDKit-validated" is a hand-curation claim, not a runtime gate.

### Permutation + pre-filter + ADMET screen + ranking
- Permutation generates analogs by applying allowed SMIRKS to TARGET sites only. Combinatorial explosion bounded by site × strategy × per-strategy product cap.
- Pre-filter drops invalid valencies, neutral-charge violations, ring-system breaks.
- ADMET screen uses the engine inventoried in §1.
- **"Pareto" ranking is a weighted scalar sum** (`ranking.py:276-291`) — sorted by `total_score = sum(weight_i * score_i) * penalty_multiplier`. Not a Pareto front. Name comes from API field convention.

### SYBA integration
Verified Rule 36 across orchestrator, permutation, ranking, report, CSV. `syba_score` is primary; `hard_probability` from GASA-style records kept for audit.

### Reports
PDF/HTML/CSV all show SYBA Score + Verdict + Confidence + structural depiction. CSV export was restructured (commit reads `admet.get("GASA") or admet.get("gasa_score") or {}` with fallback). WeasyPrint render fix (single CSS line) verified.

### Email delivery bug surface
- Worker queries `users` table (`worker.py:213`).
- Endpoint queries `profiles` table (`endpoints/lead_optimizer.py:294`).
- Same user, two source-of-truth tables. The endpoint path silently fails email lookup. Bug to fix; flag in paper if email-delivery is claimed.

### Tests
- **38 tests** in `test_lead_optimizer.py`.
- Cover schema back-compat, multi-residue round-trip, atom_indices, Murcko detection for aspirin, methyl atom-index distinctness, scaffold SMARTS, peripheral-methyl-on-pyridine, scaffold-smarts idempotency, label resolution, chemistry validator.
- **No end-to-end `run_lead_optimization` integration test.**
- **No analog-quality validation evidence** — no MMPDB comparison, no matched-molecular-pair recovery rate, no baseline comparison to public generators (Reinvent, MOSES, GuacaMol).
- **No benchmark of vision-model accuracy on a held-out LID set.**

### What's solid / partial / missing
**Solid:** 12-stage pipeline wiring, per-instance SMARTS labelling, SYBA-anchored ranking, soft Murcko gate, chemistry validator, schema back-compat with multi-residue support.
**Partial:** STRUCTURAL_CORE removal (field still exists), Vision provider chain (Scout in code, Maverick in docstring), MiniMax M3 disabled by default, SMIRKS library size claim 3× actual.
**Missing:** end-to-end integration test, analog-quality benchmark, vision-accuracy benchmark on held-out LIDs, MMP recovery rate vs MMPDB baseline. **This is exactly the validation that Phase 3 must build.**

---

## 3 — Deep Research pipeline
**Detail:** `paper/notes/03_deep_research.md`

### Nodes
Four agentic nodes: **planner → researcher → reviewer → writer**, plus a single-pass fallback and a "deep_research_elite" variant.
- Planner: Groq `openai/gpt-oss-120b` for JSON plan output.
- Researcher: same Groq model, multiple rounds, search-result triage.
- Reviewer: same Groq model, gap-filling pass.
- Writer: **OpenCode Go DeepSeek V4 Pro** at `max_tokens=24576` (`deep_research.py:1804`). CLAUDE.md still says "8K budget" — doc drift.

### Search backends actually invoked
- **PubMed E-utilities** (`literature_service.py` + `pubmed_service.py`)
- **Serper Google Scholar** (paid API for scholarly search)

The other rules-table sources — Semantic Scholar, OpenAlex, arXiv, bioRxiv, medRxiv, DuckDuckGo, CrossRef — exist as service files but **are not invoked** from the deep-research pipeline. Rule 19 fallback chain is broader on paper than in code.

### Citation handling
- Extraction: 5 regex patterns + `SequenceMatcher` fuzzy author match (threshold 0.85) to map in-text citations to the references list.
- Filter: drops citations the model invented (not in references). Does **not** verify that real cited papers support the claims attributed to them.
- `save_checkpoint` mutation bug (Rule 34) is fixed — `_scrub` deep-copies the checkpoint, the live state is left intact.
- `create_response_branch` is called (Rule 32 honoured).
- `clean_unicode_for_pdf(None)` is None-safe (Rule 33).
- SSE step_complete try/except/finally is in place (Rule 15).

### `EvidenceValidator` is dead code
- Defined at `evidence_validator.py:12` (142 lines), unit-tested in `tests/`.
- **Never imported** by `deep_research.py`, `research_tasks.py`, `ai.py`, or the container.
- What it actually computes is study-design strength (e.g. RCT vs case report), not claim-source verification.
- A paper claiming "evidence-validation" needs to wire this in OR build a real claim→source verifier.

### NAPLEX evaluation
**Zero hits across backend / frontend / tests / scripts / docs.** No NAPLEX test bank, no evaluation script, no accuracy log, no per-question outputs.

### Citation faithfulness
**Not measured.** No harness fetches a cited source and checks whether the cited paper supports the claim. `_verify_citation_density()` measures density (citations per paragraph), not faithfulness.

### PDF + email delivery
WeasyPrint primary, xhtml2pdf + reportlab fallbacks. None-safe path implemented. PDF generation succeeds; email path uses Resend or SMTP (the latter has the leaked-credential issue in §8).

### What's solid / partial / missing
**Solid:** 4-node agentic flow, SSE streaming, citation extraction with fuzzy match, PDF generation, checkpoint safety.
**Partial:** Search backend breadth (2 sources, not 7+), token-budget docs drift, EvidenceValidator orphan.
**Missing:** NAPLEX evaluation, citation faithfulness measurement, claim→source verifier, comparison to plain-LLM baseline.

---

## 4 — LLM routing, RAG, Table Intelligence
**Detail:** `paper/notes/04_routing_rag_tables.md`

### (a) LLM routing
- Provider classes: Pollinations, OpenCode Go OAI-compat, Groq, Mistral, NVIDIA NIM. The Anthropic-compat endpoint exists but is **not wired into `multi_provider.py`** — the Vision Agent has its own dedicated path (`vision_agent.py:43`, x-api-key headers).
- NVIDIA NIM still initialised at startup ("Primary — 80% weight" banner) but **not in any `MODE_PRIORITIES` list**. Reachable only via dead-letter random fallback. The banner is misleading.
- `MODE_PRIORITIES` has one `deep_research` key — not separate planner/researcher/reviewer/writer keys. Those distinctions are **caller-side conventions**, not router config.
- SSE parser reads only `delta.content` (`multi_provider.py:602`); `reasoning_content` is silently dropped. Rule 30 is accurate.
- `PROVIDER_CONTEXT_WINDOWS` and 7500-token Groq eager-skip are present and correct.

### (b) RAG
- Embedding: **Mistral `mistral-embed-1024`**. `CohereEmbeddingsService` exists as 403 lines of dead code — factory never returns it.
- **Two competing chunk-size configs**: `RAGConfig.CHUNK_SIZE = 1500` vs `settings.LANGCHAIN_CHUNK_SIZE = 1000` (the one `text_splitter.py` actually uses). Rule 37 consolidation is half done.
- **Embedding version drift**: `rag.py` stamps `"mistral-v1"`; `enhanced_rag.py` stamps `"v1-mistral-embed-1024"`. Same vectors, two version strings. The registry validator could catch this but no production path calls it.
- **No external reranker**. `rerank_chunks` is lexical Jaccard + Reciprocal Rank Fusion only. No Cohere rerank API call.
- Page numbers stored in metadata but **not surfaced in the LLM prompt** — citation granularity is filename-only.
- Vector store: Supabase pgvector. Confirmed.

### (c) Table Intelligence
- Module layout: `schema/`, `intent/`, `indication/`, `gates/`, `output/`, `audit/`, `orchestrator.py`.
- **7 GateSets verified**: `cns_v1`, `cns_vulnerable_v2`, `oral_systemic_v1`, `topical_v1`, `antibacterial_v1`, `oncology_v1`, `ophthalmic_v1`. Each carries hard-gate criteria, uncertainty margins, optional structural SAR levers (gated on SMARTS preconditions).
- Detector confidence floor at 0.7 when binding columns (docking, MMGBSA) are present — verified (`schema/detector.py:185-186`).
- Audit + replay: Supabase `table_intelligence_audit` table (migration 025), REST endpoint `/api/v1/table-intelligence/replay/{audit_id}` with RLS. **`replay.py` docstring promises a `mode='live'` re-execution** but the function takes no `mode` parameter. Live-replay is aspirational.
- Structural SAR: levers gated on functional-group presence — won't tell a compound to "lower basic-amine pKa" if it has no basic amine.
- 45 distinct `def test_*` functions in `test_table_intelligence.py` (parametrise blocks inflate the collected count).
- LLM-fallback for ambiguous intent/indication: documented in docstrings but **keyword-only as of this commit**.

### What's solid / partial / missing
**Solid:** Multi-provider with documented fallback chains, RAGConfig as single-source for some knobs, deterministic gating with versioned GateSets, audit log with RLS.
**Partial:** Anthropic endpoint partial integration, RAG chunk-size + embedding-version split, GateSet replay live-mode aspirational.
**Missing:** NVIDIA NIM should be either re-wired or removed (currently dead+stale-banner); external reranker; page-level citation in RAG; LLM-fallback intent classifier.

---

## 5 — DDI, docking, frontend, tests, benchmarks, infra
**Detail:** `paper/notes/05_remainder.md`

### DDI
- Advertised: NLM RxNav.
- File admits: "Interaction endpoints are largely discontinued, so this often falls through" (`ddi_service.py:185`).
- Real signal: `_check_interaction_ai()` — the platform LLM.
- No DrugBank dump, no PMID-grounded evidence. **A paper claiming a DDI analyzer must frame it as an LLM-driven assistant, not a curated-database lookup.**
- Endpoints live on the chat router: `/api/v1/chat/ddi/check`, `/api/v1/chat/ddi/polypharmacy`.

### Docking / Schrödinger / MCP
- **Not in repo.** Grep hits for "schrodinger / vina / autodock / glide / mmgbsa" are exclusively (a) `column_registry.py` aliases for parsing user-uploaded CSVs, (b) stored artifacts, (c) planning docs.
- `grep -ri "mcp" backend/` returns zero.
- The platform **reasons over** user-supplied docking outputs (via Table Intelligence); it does **not** compute binding affinities. This must be honest in the paper.

### Image generation
- **Single-provider: Pollinations.ai (`qwen-image` default).** No FLUX/DALL-E/Midjourney despite Rule 14 prose. No fallback chain. R2 storage wired.

### Frontend
- Next 14.0.4, `output: 'export'` (fully static).
- 55 component `.tsx` files.
- **Exactly two test files**: `useChatState.test.tsx`, `editMessage.test.tsx`.
- `TokenStreamer` claim verified — 135 lines, pure logic, no React deps.

### Test suite — exact counts
- **748 `def test_` definitions across 47 files** in the backend.
- **Regression suite (the one CI runs): ~280 tests across 14 files**.
- CLAUDE.md's "190 / 293 / 307" numbers are historic snapshots that don't fully reconcile with today's count. The paper should report the CI suite count from a fresh `pytest --collect-only`.

### Benchmark / evaluation harnesses
- **Zero TDC / MoleculeNet / ChEMBL imports** anywhere.
- The only file named "benchmark" is `benchmark_writer_providers.py` measuring LLM latency + word count — not accuracy.
- **Any paper-grade ML claims must be built outside this repo in Phase 3.**

### Datasets in repo
- `drugPool.ts`: **129 entries**, not the claimed "500+".
- No held-out evaluation set, no gold-standard annotations.
- Supabase migrations have audit-log table for Table Intelligence (025) and earlier schema. No seed data.

### Infra
- `deploy.sh`, `setup-dcv-fixed.sh`.
- PM2: `pharmgpt-api` (port 7860), `admet-engine` (port 7861).
- Contabo VPS (4 vCPU / 8 GB).
- Vercel for frontend.
- ServiceContainer: **39 registered slots** (CLAUDE.md "24" is stale).

### Documentation
- `README.md`, `gemini.md`, `CLAUDE.md`, `.kiro/context/` (a few files; many `.kiro/*.md` were deleted in the current working tree).

### Security finding (separate from paper task — flag for rotation)
- **SMTP credentials inlined in `backend/ecosystem.config.js:9-11`.** This file is in version control. Whatever credentials live there should be rotated before the repo is archived for a citable code release (Phase 6). The credentials themselves are not for the paper; the action is to move them to `/home/ubuntu/.env` and re-issue.

---

## 6 — Doc-vs-code drift table (must be reflected in the paper)

These are the numbers/claims where what the docs say is **not** what the code does. Every one of these must be corrected (in code or in the paper) before any quantitative claim is made.

| Claim in docs / prompts | Reality in code | Source |
|---|---|---|
| 104 ADMET endpoints | **54** surfaced in UI; "104" is a pydantic default | §1 |
| ~~479 SMIRKS entries~~ | **CORRECTED 2026-06-10:** Phase 1 grep miscounted; the true count, by `from app.services.lead_optimizer.smirks_library import SMIRKS_LIBRARY; len(SMIRKS_LIBRARY)`, is **479** across **22 distinct category-field values** and 35 distinct key prefixes. CLAUDE.md was right. | §2 |
| 500+ drugs in drugPool | **129 entries** | §1, §5 |
| 24 services registered | **37 slots** in ServiceContainer (counted `self._services['...']` assignments at `backend/app/core/container.py`); earlier inventory said 39 — both differ from CLAUDE.md's "24". Final number: 37. | §5 |
| Llama 4 Maverick 17B-128e Tier-1 vision | Code ships **Scout 17B-16e** | §2 |
| MiniMax M3 Tier-1 vision (CLAUDE.md 2026-06-05) | Env-gated, **disabled by default**; real Tier 1 is **Kimi K2.6** | §2 |
| "Pareto" ranking | **Weighted scalar sum**, sorted by `total_score` | §2 |
| Writer node 8K budget | **24576 tokens** at `deep_research.py:1804` | §3 |
| NVIDIA NIM "Primary — 80% weight" | Not in any `MODE_PRIORITIES`; dead-letter fallback only | §4 |
| `MODE_PRIORITIES["deep_research_planner/researcher/reviewer/writer"]` | Single `deep_research` key; rest are caller-side conventions | §4 |
| RAGConfig CHUNK_SIZE = 1500 | Code path uses `settings.LANGCHAIN_CHUNK_SIZE = 1000` | §4 |
| Single embedding-version stamp | Two distinct stamps in `rag.py` vs `enhanced_rag.py` | §4 |
| ADMETlab 3.0 prediction fallback | Only `wash_molecule()` calls ADMETlab; prediction path is local → RDKit | §1 |
| Semantic Scholar + OpenAlex + arXiv + bioRxiv + medRxiv + DuckDuckGo in deep research | Only **PubMed + Serper** are invoked | §3 |
| 190 / 293 / 307 test count | **~280 in regression CI**, 748 total `def test_` | §5 |
| "all RDKit-validated" SMIRKS | `validate_entire_library()` exists but is **never called** | §2 |
| Evidence validator wired | Defined + tested but **never imported** in pipeline | §3 |
| GASA primary synth metric | **SYBA is primary**; GASA `.pth` inert because `dgl` not installed | §1 |
| STRUCTURAL_CORE removed | Removed from prompt; **field still exists**, payload auto-merged | §2 |

---

## 7 — What can be honestly validated in Phase 3

Given the inventory above, the validation runway looks like this (in priority order):

### Tier 1 — Feasible with code as-is + standard public datasets

1. **TDC ADMET Benchmark Group** — run the existing engine (via `pip install pyTDC` + `admet_ai`) on the TDC ADMET Benchmark Group tasks using prescribed scaffold splits. Report metrics next to the published leaderboard. The model is upstream's, so this is essentially a faithful re-implementation check + Benchside's directional-scoring layer applied. **Most credible single experiment.**
2. **Lead-optimization end-to-end case study** — pick a single target (DYRK1A or PBP2a per user precedent) and run the 12-stage pipeline. Report: number of valid analogs generated, SYBA distribution, ADMET-pass rate, PAINS/Brenk filter rate, fraction with conserved Murcko scaffold, fraction with conserved pharmacophore atoms. **Quantitative without requiring ground truth.**
3. **Matched-molecular-pair recovery** — on a public MMPDB / ChEMBL-derived MMP dataset, test whether the SMIRKS-driven permutation proposes the empirically-observed improving transformation. Report recall@k for the top-ranked analogs. **The strongest single claim the Lead Optimizer could carry.**
4. **Citation faithfulness sample** — take 50 deep-research reports, fetch each cited paper (PubMed / DOI), and manually grade whether the cited paper supports the in-text claim. Report fraction-real vs fraction-hallucinated. **This is the experiment that converts "deep research" from claim into evidence.**

### Tier 2 — Feasible with modest new code

5. **PAINS / Brenk filter audit on a baseline generator** — run the permutation engine vs Reinvent or MOSES on the same lead, compare structural-alert rates. Position Benchside as the more chemistry-aware generator.
6. **NAPLEX-style accuracy** — if the user has a question bank or can curate ~200 from public sources, run the chat path with/without RAG and report accuracy. Compare to a plain-LLM baseline (Groq with no tools). Hallucination measured as fraction of answers with at least one unsupported clinical claim.
7. **Table Intelligence reproducibility** — repeat-run the same uploaded CSV 10× and report decision agreement. Audit-log replay validates determinism.

### Tier 3 — Aspirational, would need scope expansion

8. Synth-accessibility human-rater agreement (SYBA vs medicinal chemist labels).
9. Vision-Agent accuracy on a held-out LID set (would need to build the gold set).
10. Comparison of agentic deep-research output to plain-LLM survey on a literature-search benchmark.

---

## 8 — Critical gaps to fix before the paper ships

These are not "nice to haves" — these are integrity blockers:

1. **Doc-vs-code drift items in §6 must each be either fixed in code or honestly recorded in the methods section.** The SMIRKS-count item is closed (verified 479, not 167; CLAUDE.md was correct). Remaining drift items (ADMET endpoint count surfaced in UI, NVIDIA NIM banner stale, RAG chunk-size mismatch, etc.) still need adjudication.
2. **EvidenceValidator must be wired in or removed.** Defined-tested-orphaned is the worst of all worlds for peer review.
3. **`validate_entire_library()` must run in CI** or the "all RDKit-validated" claim drops.
4. **Live state of MiniMax M3 vs Kimi K2.6 vs Llama 4 Scout** must be documented accurately in the methods section.
5. **The `users` vs `profiles` table split in lead-optimizer email path** is a real bug — fix it or drop email claims.
6. **Leaked SMTP credentials in `ecosystem.config.js`** must be rotated and moved to `.env` before any Zenodo archive.
7. **Test count for the paper must come from a fresh `pytest --collect-only`**, not from CLAUDE.md history.
8. **Schrödinger / docking / MCP must NOT appear in the paper as platform capabilities.** They're not in the repo. The paper can honestly describe the platform as "reasoning over user-provided docking output," which is in fact what Table Intelligence does.

---

## 9 — Component-to-detail-file index

| Component | Detail file |
|---|---|
| ADMET engine + SYBA | `paper/notes/01_admet.md` |
| Lead Optimizer (vision, SMARTS, SMIRKS, ranking, reports) | `paper/notes/02_lead_optimizer.md` |
| Deep Research (planner, researcher, reviewer, writer) | `paper/notes/03_deep_research.md` |
| LLM routing + RAG + Table Intelligence | `paper/notes/04_routing_rag_tables.md` |
| DDI, docking, image-gen, frontend, tests, benchmarks, infra | `paper/notes/05_remainder.md` |

The detail files are the authoritative source for every file:line citation. This document is the synthesis.
