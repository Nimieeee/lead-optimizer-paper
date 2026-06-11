# Benchside Platform Inventory, Remainder

Covers: DDI analyzer, docking/Schrödinger/MCP, image generation, frontend
architecture, test totals, evaluation harnesses, bundled datasets, deploy
infra, in-repo documentation. Other agents cover ADMET, Lead Optimizer,
Deep Research, and routing/RAG/TableIntelligence.

Source citations are file paths with line numbers. Where a capability is
absent, this note says so explicitly.

---

## 1. DDI analyzer

**Backend service** lives at `backend/app/services/ddi_service.py` (707 lines,
`DDIService` class starting line 19).

**Data source, primary:** NLM RxNorm + RxNav REST APIs
(`RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"`, line 31). Drug names are
resolved to RxCUI identifiers via `/rxcui.json?name=...&search=1` fuzzy
search (`resolve_drug`, line 59), with a hardcoded fallback dictionary
covering 11 common drugs, aspirin, warfarin, simvastatin, ketoconazole,
methotrexate, tetracycline, ibuprofen, acetaminophen, naproxen, insulin,
calcium (lines 76-87). The actual interaction lookup hits
`/interaction/interaction.json` with `sources=ONCHigh DrugBank`
(line 187-191).

**Data source, fallback (where the real work happens):** the NLM
interaction endpoints are largely discontinued, which the file itself
acknowledges in a comment at line 185
(`Note: Interaction endpoints are largely discontinued, so this often falls
through`). When the API returns empty, the service falls through to
`_check_interaction_ai()` (line 239), which prompts the platform LLM
through `ai_service` (resolved via container, lines 52-57) and asks it to
return structured JSON. The system prompt
(`backend/app/services/ddi_service.py:247-271`) frames the assistant as a
"senior clinical pharmacologist" and requests `severity`, `description`,
`mechanism`, `clinical_significance`, `evidence_level` as flat strings.
**There is no curated DrugBank dump, no PubChem integration, no internal
DDI database. Severity and mechanism explanations come from the LLM, not
from a validated knowledge base.**

**Severity scoring** is a 7-entry string map (line 34-42) translating
RxNorm verbs (`contraindicated`, `serious`, `significant`) to
`Major | Moderate | Minor | Unknown`. The `_classify_severity` helper
(line 372) does keyword scanning on the LLM-generated description
+ mechanism strings when severity is missing.

**Supporting evidence / citations:** none. The `evidence_level` field is
a free-text string the LLM produces (e.g. "High - Clinical Trials and
FDA Labeling"); there is no PMID, no DOI, no link-out, no auditable
source. `_estimate_evidence()` (line 465) heuristically returns
`"Strong"` / `"Moderate"` / `"Limited"` by looking for the strings
"trial" / "study" / "case report" in the description.

**Polypharmacy:** `check_polypharmacy()` (line 532) does all C(n,2)
pairwise checks (loops the same `check_interaction` two at a time, no
parallelism). `generate_polypharmacy_summary()` (line 568) sends the
list of pairwise interactions back to the LLM for a holistic clinical
narrative, `overall_risk`, `cumulative_mechanisms`,
`management_strategy`, `therapeutic_alternatives`,
`monitoring_recommendations`, `timeline`.

**Endpoints:** registered on the chat router, not a dedicated DDI router
, `backend/app/api/v1/endpoints/chat.py:748` (`POST /api/v1/chat/ddi/check`)
and `backend/app/api/v1/endpoints/chat.py:788`
(`POST /api/v1/chat/ddi/polypharmacy`). There is **no** standalone
`endpoints/ddi.py` file.

**Frontend:** `frontend/src/app/(hub)/ddi/page.tsx` (12 lines, thin
wrapper) → `frontend/src/components/ddi/DDIDashboard.tsx` (390 lines,
single component, single↔poly toggle, severity colour map at
lines 65-72, emoji severity badges at 74-79). Hook:
`frontend/src/hooks/useDDI.ts` (146 lines) defines `DDIInteraction` and
`PolypharmacyResult` TypeScript types and fetches the two endpoints. A
secondary inline result component lives at
`frontend/src/components/chat/DDIResult.tsx` (rendered in the chat
stream when DDI is invoked through chat).

**Tests:** `backend/tests/test_ddi_service.py`, 24 test definitions. Not
in `tests/regression/` (so excluded from the canonical regression
sweep).

---

## 2. Docking + Schrödinger + MCP

**Honest answer: there is no docking engine in this repo.** Docking
scores come from user-uploaded CSV/SDF files that TableIntelligence
parses.

Concrete evidence:

- `grep -ri "schrodinger"` over `backend/` and `frontend/` hits only
  `backend/app/services/table_intelligence/schema/column_registry.py`
  (column-name aliases for ingested files) and two stored uploaded
  artifacts (`backend/test_files/top_20_mmgbsa.sdf`,
  `backend/data/reports/report_*.html`). No SDK, no licence wrapper, no
  Maestro/Glide/Jaguar subprocess calls.
- `grep -ri "autodock\|vina\|glide\|maestro"` returns hits only in
  `column_registry.py:35-39`, `docs/plan_e_opensource.md`
  (a planning doc, not code), `data/medchem_knowledge/` (textbook
  extractions), and the stored upload artifacts. The column registry
  (`backend/app/services/table_intelligence/schema/column_registry.py:34-39`)
  defines aliases, `docking_score`, `mmgbsa`, `glide_emodel`, purely
  for **parsing** what users upload, not for **computing** anything.
- `grep -ri "mmgbsa"` finds only narration/threshold code in
  `table_intelligence/gates/library.py`,
  `table_intelligence/output/optimization.py`, the same column registry,
  and `app/services/ai.py` / `deep_research.py` (string literals in
  prompts). No prime-mmgbsa, no `mmgbsa.py` calculator.
- `grep -ri "mcp"` (Model Context Protocol) over `backend/` returns
  zero hits. **There is no MCP server, no MCP client, no MCP tool
  exposure in this repo.**

What actually exists for binding scores: TableIntelligence reads
docking_score / MMGBSA columns from uploaded CSV/SDF and applies
deterministic gates (e.g. the CNS gate set at
`backend/app/services/table_intelligence/gates/library.py` requires
MMGBSA to beat 3 of 4 reference compounds, but the reference values
were uploaded, not computed in-platform). The platform is, in this
domain, a **reasoning layer over user-supplied docking output**, not a
docking pipeline.

The Lead Optimizer does no docking either, it operates on RDKit-
computed properties and SYBA synthetic accessibility
(`backend/app/services/sas_service.py`, `gasa_service.py`,
`gasa_model/`), permutes via SMIRKS, and ranks. No binding-affinity
prediction is in scope.

---

## 3. Image / structure generation

**Single backend file:** `backend/app/services/image_gen.py` (155 lines).
`ImageGenerationService` (line 27).

**Provider:** Pollinations.ai only, `POLLINATIONS_BASE_URL =
"https://gen.pollinations.ai/image"` (line 24). Default model
`qwen-image` (line 47 default arg). The function URL-encodes the prompt
and GETs `https://gen.pollinations.ai/image/{prompt}?model=...&width=512&height=512&nologo=true&safe=true&seed=...`
(lines 122-149).

**No multi-provider fallback chain for image generation.** This is a
single-provider pipeline. If Pollinations fails, the user gets an error
dict `{"status": "error", "error": str(e)}` (line 114-120). No FLUX
direct API, no DALL-E, no Stable Diffusion, no Midjourney code path ,
the platform calls `qwen-image` through Pollinations and that's it.

There is an exploratory test script `backend/tests/test_image_models.py`
that probes alternative Pollinations models (`flux`, `zimage`,
`imagen-4`, `grok-imagine`, `klein`, `klein-large`) by name (lines
16-23), but the production service hardcodes the `qwen-image` default.

**Storage:** generated images are uploaded to Cloudflare R2
(`backend/app/services/image_gen.py:33-43`, `boto3` S3 client against
`{R2_ACCOUNT_ID}.r2.cloudflarestorage.com`) and a public R2 URL is
returned. No base64 inline path is used in production
(line 110: `"image_base64": None`).

**Prompt engineering / Rule 14 enforcement:** the service has hardcoded
style-keyword routing for medical content (lines 58-79), diagram
prompts get "medical textbook diagram, anatomically correct
cross-section, ..." appended; pathology prompts get a separate template;
both add a negative-prompt clause. The Rule-14 "diagrams should route
to Mermaid not images" is enforced upstream in `ai.py`, not here ,
`backend/app/services/ai.py:238` describes the image-gen tool to the
LLM as "Use this ONLY when the user EXPLICITLY asks you to 'generate
an image' ... Do NOT use this for diagrams". The text-to-Mermaid path
is in `backend/app/services/mermaid_validator.py` and
`chat_orchestrator.py:108` (`self.mermaid.fix_markdown_mermaid`).

**Vision service** (separate, `backend/app/services/vision_service.py`,
685 lines) is for analysing user-uploaded images / PDFs / PPTX, not
generation. It has Docling + PyMuPDF + python-pptx parsers with a
full-vision fallback (lines 89-323) and the `VisionService` class at
line 560 with `analyze_image()` / `analyze_image_bytes()`.

---

## 4. Frontend architecture

**Framework:** Next.js 14.0.4, React 18.2.0, TypeScript, Tailwind
(`frontend/package.json:13-21`). Next config is `output: 'export'` ,
the FE is a fully static export, not SSR
(`frontend/next.config.js:3`). State via React Context API
(`useChat` ↔ `ChatContext`, `SidebarContext`).

**Route structure:**
- `frontend/src/app/(hub)/`, route group sharing one layout
  (`layout.tsx`). Subroutes: `lab/`, `studio/`, `literature/`, `ddi/`,
  `memories/`. Created 2026-05-29 to fix sidebar remount flicker
  (CLAUDE.md fix entry).
- `frontend/src/app/chat/`, standalone (not in hub group). 824 lines
  in `page.tsx`, main chat surface.
- `frontend/src/app/`, auth pages (`login`, `register`,
  `forgot-password`, `reset-password`, `verify`), marketing
  (`about`, `pricing`, `faq`, `support`, `terms`, `privacy`, `docs`),
  `admin/`, `profile/`, `changelog/`, `models/`, `lab-report/`.

**Contexts** (`frontend/src/contexts/`):
- `ChatContext.tsx` (22 lines), thin wrapper around `useChat()` hook.
- `SidebarContext.tsx` (15 lines), `sidebarOpen` bool only.

**Components inventory** (`frontend/src/components/`, 55 `.tsx` files
total):
- `chat/`, `ChatMessage`, `ChatInput`, `ChatSidebar`, `BranchMenu`,
  `CitationPanel`, `ClarifyingQuestionsModal`, `DDIResult`,
  `DeepResearchCard`, `DeepResearchModal`, `DeepResearchUI`,
  `HandoffButton`, `LongPressMenu`, `MarkdownRenderer`,
  `MermaidRenderer`, `MobileNav`, `PubMedResults`, `RagAdvisoryCard`,
  `StreamdownWrapper`, `StreamingLogo`.
- `lab/`, `LabDashboard`, `ADMETPropertyCard`,
  `ADMETParameterLegend`, `MoleculePreview` (the ADMET surface).
- `lead/`, `SetupWizard`, `PipelineMonitor`, `ResultsDashboard`,
  `AnalogCard`, `CampaignHistory`, `LeadProfileBar` (the Lead
  Optimizer / "Studio" surface).
- `ddi/`, `DDIDashboard` only.
- `literature/`, `LiteratureDashboard` only.
- `lab-report/`, `LabReportUI` only.
- `landing/`, `auth/`, `admin/`, `docs/`, `shared/`, `ui/`, chrome.

**Surface ↔ hub-route mapping:**
| Hub surface | Route | Top component |
|---|---|---|
| Chat | `/chat` (outside hub group) | `chat/page.tsx` (824 lines) |
| Lab (ADMET) | `(hub)/lab/` | `LabDashboard.tsx` |
| Studio (Lead Optimizer) | `(hub)/studio/` | `studio/page.tsx` (284 lines) |
| Literature (Deep Research) | `(hub)/literature/` | `LiteratureDashboard` |
| DDI | `(hub)/ddi/` | `DDIDashboard.tsx` |
| Memories | `(hub)/memories/` | `memories/page.tsx` (527 lines) |

**Hooks** (`frontend/src/hooks/`):
- `useChat.ts` (445), `useChatState.ts` (327), `useChatStreaming.ts`
  (1144), `useStreamingState.ts`, `useConversationStore.ts`,
  `useSWRChat.ts`, `use-batched-stream.ts`, chat.
- `useDDI.ts` (146), `useLeadOptimizer.ts` (663), `usePubMed.ts`
  (170), `useProjects.ts`, `use-feature-flag.ts`, `use-translation.ts`.

**TokenStreamer.** Lives at `frontend/src/utils/TokenStreamer.ts`
(135 lines). The "pure-logic, no React deps" claim in CLAUDE.md
checks out: it's a single class with a token buffer, a display
buffer, a `setTimeout`-driven dripper, and `onUpdate`/`onComplete`
callbacks. No React imports.
`frontend/src/utils/streamReader.ts` (168 lines) is the SSE
reader/parser that feeds it.

**Tests.** Two frontend test files exist:
- `frontend/src/tests/useChatState.test.tsx`
- `frontend/src/hooks/__tests__/editMessage.test.tsx`

That's the entire frontend test surface, two component/hook tests
using vitest + `@testing-library/react`
(`package.json:32-40`, `vitest ^4.0.18`). No Playwright, no Cypress,
no integration sweep. **The frontend is effectively untested.**

---

## 5. Test suite totals

Counted by `grep -c "^\s*(async )?def test_"` over every `test_*.py`
under `backend/tests/`.

- **47 test files** total under `backend/tests/`.
- **748 individual test functions** total.

Distribution (top of the long tail):

| Tests | File |
|---|---|
| 68 | `tests/test_multi_provider_unit.py` |
| 50 | `tests/regression/test_all_services.py` |
| 45 | `tests/regression/test_table_intelligence.py` |
| 40 | `tests/test_multi_provider_properties.py` |
| 39 | `tests/regression/test_admet_service.py` |
| 38 | `tests/regression/test_lead_optimizer.py` |
| 29 | `tests/test_error_handling_comprehensive.py` |
| 29 | `tests/regression/test_mermaid.py` |
| 27 | `tests/unit/test_services.py` |
| 26 | `tests/test_multi_provider_integration.py` |
| 25 | `tests/regression/test_router_services.py` |
| 24 | `tests/test_ddi_service.py` |
| 21 | `tests/regression/test_export_processor.py`-ish, citation, sdf each |

Categorisation by physical directory:

- `tests/regression/`, 14 files (the canonical "MUST pass before
  deploy" suite per CLAUDE.md). Files: `test_admet_service`,
  `test_all_services`, `test_chat_stream_422`, `test_cors_headers`,
  `test_export_processor`, `test_lead_optimizer`, `test_literature`,
  `test_literature_pdf`, `test_mermaid`, `test_rag_config`,
  `test_router_services`, `test_service_integration`,
  `test_table_intelligence`. Roughly **~280 tests** in regression
  alone by my counts.
- `tests/unit/`, 1 file (27 tests).
- `tests/integration/`, 1 file (15 tests).
- `tests/` (root), 32 files, mix of unit + integration + ad-hoc.

**Honest note on the CLAUDE.md "190 → 307 → 293" numbers:** CLAUDE.md
quotes "190 tests, ~11s on VPS" in the stack section but the recent-fix
table cites "293/293 on VPS" (Phase 5, ADMET). My count of `def test_`
across the whole `tests/` tree is **748**, which is higher than every
CLAUDE.md number. The discrepancy is because the canonical CI run
only executes `pytest tests/regression/` (per the deploy runbook
section of CLAUDE.md), not the full tree. Counting only files inside
`tests/regression/`, my arithmetic gives 50 + 45 + 39 + 38 + 29 +
25 + 11 + 9 + 6 + 5 + 5 + 4 + 3 = **279 regression tests**, plausible
neighbourhood of the "293" claim. I can't reproduce the
"190 → 307" number from disk; treat them as historic snapshots.

---

## 6. Benchmarks + evaluation harnesses

**Honest answer: there is no externally-validated benchmark harness in
this repo.**

What does NOT exist:
- `grep -ril "from tdc\|import tdc\|tdcommons"` over `backend/` returns
  **zero hits.** No Therapeutics Data Commons integration. The
  ADMET-AI microservice in production may itself have been trained on
  TDC data, but this repo does not contain code that evaluates
  Benchside outputs against TDC held-out splits.
- No `moleculenet`, no `chembl_webresource` imports.
- No `evaluation/`, `eval/`, `benchmarks/`, `metrics/` directories
  (other than the writer-comparison scripts described below).
- No NAPLEX / USMLE question set, no `grep -ril "naplex\|usmle"` hits
  outside `.venv/`.
- No held-out CSVs with ground-truth labels (the report files in
  `backend/data/reports/` are stored user uploads, not benchmark
  datasets).
- No script that produces AUROC / AUPRC / MAE / RMSE numbers.

What DOES exist (a much weaker form of "benchmark"):
- `backend/scripts/benchmark_writer_providers.py` and
  `benchmark_writer_enhanced.py`, these compare **deep-research writer
  output across LLM providers** (Mistral, Pollinations gpt-5-mini,
  Gemini Fast, Claude Airforce, OpenAI). They measure
  `response_time_seconds`, `output_length_chars`, `word_count`,
  `sections_found`, `references_count`, i.e. **latency and surface
  metrics**, not factuality, accuracy, or correctness against a gold
  set. Results saved as JSON to
  `backend/scripts/benchmark_reports/enhanced_benchmark_20260319_062321.json`
  (one timestamped run, 2026-03-19).
- `backend/scripts/latency_test.py`, manual latency measurements
  (OpenFDA fetch, Mistral embedding gen, ...). Not a benchmark suite.

**Implication for a paper:** any quantitative ML claims (ADMET accuracy,
SYBA discrimination, deep-research factuality) would need to be backed
by harnesses that **do not exist in this repo**. They would need to be
built against TDC ADMET held-outs, MoleculeNet, or a curated
hand-labelled set.

---

## 7. Datasets included in repo

**`frontend/src/constants/drugPool.ts`**, 182 lines, **129 drug
entries** (confirmed by `grep -cE "^\s*\{\s*name:\s*'"`). TypeScript
`DrugSuggestion` shape: `{ name, smiles, year?, class }`. Used by
`LabDashboard.tsx` for the "random suggestions" pill row. Grouped by
therapeutic class in source comments (NSAIDs, Cardiovascular, Statins,
ACE inhibitors, Anticoagulants, JAK inhibitors, CGRP antagonists, etc.,
spanning 1827 morphine → 2024 rimegepant). NOT a benchmark set, UI
suggestion list only. CLAUDE.md's "500+ drug suggestions" claim is off
by ~4×; the actual file has 129.

**`backend/data/medchem_knowledge/`**, RAG-ingested medicinal chemistry
extractions:
- `brown_ch6-10_extraction.txt`, `wilson_ch3-28_extraction.txt`
  (textbook extractions).
- `admet_strategies.md`, `bioisosteres.md`, `structural_alerts.md`.
- `glaxo_structural_alerts.csv`, `extracted_transformations_2026-04-24.md`
  (SMIRKS feedstock for the Lead Optimizer permutation engine, the
  "344 → 479 entries" referenced in CLAUDE.md's 2026-04-24 row).

**`backend/data/reports/`**, stored user upload artifacts
(`report_*.sdf`, `report_*.html`, `report_*.pdf`). NOT curated ground
truth.

**`backend/test_files/`**, sample uploads for development (`admet.xlsx`,
`top_20_mmgbsa.sdf`, `Acute Toxicity.pptx`,
`Artemisinin for Cancer research.txt`, `tolu-result.docx`, etc.). Ad-hoc.

**`backend/migrations/`**, 31 SQL migration files
(`000_fix_function_conflicts.sql` … `025_table_intelligence_audit.sql`).
Schema only; no seed data beyond `002_create_admin_user.sql`.

---

## 8. Deployment + infra

**Production topology** (verified against `CLAUDE.md`, `deploy.sh`,
`backend/ecosystem.config.js`):

- **Frontend:** Vercel auto-deploy from `master` branch on push.
  `next.config.js` uses `output: 'export'`, static export.
  Production domain: `benchside.app` (per `README.md`).
- **Backend:** Contabo VPS `ubuntu@173.212.213.228` (4 vCPU / 8 GB
  RAM per CLAUDE.md). Path `/var/www/benchside-backend/backend/`.
  Runs under PM2 as `pharmgpt-api` on port 7860.
- **ADMET microservice:** same VPS, separate PM2 process
  `admet-engine` on port 7861, separate venv at
  `/home/ubuntu/admet_research/venv_admet/`. Health check
  `curl http://localhost:7861/health`.

**`deploy.sh`** (46 lines, `/Users/mac/Desktop/phhh/deploy.sh`):
1. `python3 -m py_compile backend/main.py` (syntax gate).
2. `rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc'
   --exclude '.env'` to the VPS path.
3. SSHs in, preserves existing `.env` (otherwise copies from
   `.env.production.template`).
4. `pm2 restart pharmgpt-api --update-env`.
5. Health check loop hitting `http://localhost:7860/health` 5 times
   with `sleep 10` between retries, then a final hit to
   `https://173-212-213-228.sslip.io/health`.

**`backend/ecosystem.config.js`**, single PM2 app spec. Inlines SMTP
credentials in `env` block (lines 9-11), **this is a real secret leaked
into a committed file**, worth flagging.

**`setup-dcv-fixed.sh`** (159 lines), AWS DCV / GUI session setup
helper, unrelated to the API deploy path. Likely for the developer's
remote workstation.

**Other infra scripts** (`backend/scripts/`):
- `setup-new-vps.sh`, `setup-admet-engine.sh`, `setup-monitoring.sh`,
  `verify-new-server.sh`, `check-new-server.sh`,
  `monitor-backend-health.sh`, `kill-zombie-processes.sh`,
  `continuous-monitor.py`, `monitor-research-live.py`,
  `watch-research-realtime.py`, operational tooling.

**ServiceContainer:** `backend/app/core/container.py` (301 lines). The
container holds **39 registered service slots** (counted by
`grep -cE "self\._services\["`). CLAUDE.md's "24 services registered"
is stale by ~15, more services have been added since that prose was
written (skill_service, ddi_service, export_processor, admet_processor,
prompt_processor, router_service, local_queue, etc.).

---

## 9. Documentation in repo

**`README.md`** (repo root), frontend-focused. Production URL,
Vercel deploy, dev setup, env vars, repo structure. Public-facing
project README.

**`CLAUDE.md`**, the canonical agent-memory artifact (described in
detail in the system context above). Living source of truth for
stack, deploy, rules, recent fixes.

**`gemini.md`**, parallel agent-memory artifact for Gemini. Largely
duplicates CLAUDE.md content, somewhat stale (says "24 services
registered" still).

**`.kiro/context/`**, the live working-memory directory:
- `ACTIVE.md`, current production status / in-flight work.
- `deploy.md`, deployment runbook (commands extracted out of CLAUDE.md).
- `INDEX.md`, meta-doc explaining the directory's discipline (only
  docs future work needs to consult live here).

**`backend/docs/`**, 8 planning markdowns: `lead_optimizer_plan.md`,
`plan_a_rdkit_engine.md`, `plan_b_medchem_rag.md`, `plan_c_agents.md`,
`plan_d_orchestrator.md`, `plan_e_opensource.md`, `plan_f_deployment.md`,
`plan_g_frontend.md`. These are the original Lead Optimizer build
plans; some are partly stale post-implementation.

**`docs/`** (repo root), 27 markdowns covering historical
investigation logs, architecture snapshots
(`deep_research_architecture.md`, `lead_optimizer_architecture.md`),
implementation plans (`implementation_plan_admet.md`,
`implementation_plan_year1.md`, etc.), feature deep-dives
(`r2-image-storage.md`, `pdf-generation-integration-plan.md`,
`gasa_integration_plan.md`), and post-mortems
(`deep-research-debugging-results.md`, `lessons-learned-2026-03-25.md`).
A large chunk is no longer current, these are historic, not
authoritative.

**Top-level scattered `*_FIX*.md` / `*_PLAN*.md` files** (e.g.
`413_FIX_PROVIDER_FALLBACK.md`, `COMPREHENSIVE_FIX_PLAN.md`,
`DECOUPLING_SUMMARY.md`, `DEEP_RESEARCH_FIX_SUMMARY.md`), historic
sprint artifacts left in the working tree. Per CLAUDE.md discipline,
these should have been pruned once the rules they document landed in
the Rules table. They are **not authoritative**; if they conflict with
CLAUDE.md, CLAUDE.md wins.

---

## What's solid / What's partial / What's missing

**Solid (production-grade, well-tested, clearly defined):**
- DDI plumbing, RxNav resolution + LLM fallback + polypharmacy
  pairwise expansion, has 24 backend tests and a fully-wired FE
  surface.
- Image generation, single-provider but production-deployed with R2
  storage and prompt-engineering routing.
- ServiceContainer DI pattern, 39 services, lazy-loaded, used uniformly
  by endpoints.
- Regression test suite categorisation, 14 files in `tests/regression/`
  is a clean, identifiable canonical sweep.
- TokenStreamer, actually is pure-logic-no-React-deps as advertised
  (135 lines, framework-free).
- Deploy pipeline, single `deploy.sh`, PM2-driven, health-checked.
  Reproducible.

**Partial (works, but has rough edges or unverifiable claims):**
- DDI severity scoring, for the common case where RxNav has no data,
  severity is **LLM-generated**, not from a curated KB. Acceptable for
  a clinical assistant; not citable for a research paper.
- Test totals, 748 total `def test_` across the whole tree but only
  the `regression/` subset (~280) runs in CI. CLAUDE.md numbers
  (190, 293, 307) are historic snapshots and don't reconcile precisely.
- DocumentLoader → TableIntelligence pipeline handles uploaded docking
  output, but the platform has no docking computation itself.
- Frontend test coverage, exactly two test files. Functional, but
  near-zero coverage.
- drugPool, 129 entries vs. the "500+" claim in CLAUDE.md. UI works
  fine; the headline number is wrong.

**Missing (explicitly absent, important to be clear about):**
- **No docking engine.** No AutoDock Vina, no Glide, no Schrödinger
  SDK, no GNINA, no Smina. The platform reasons over docking output
  uploaded by the user.
- **No MCP (Model Context Protocol) integration.** Zero hits.
- **No external benchmark harness.** No TDC, no MoleculeNet, no
  ChEMBL benchmark wiring. The closest thing is a one-shot
  writer-provider latency comparison from March 2026
  (`benchmark_writer_*.py`), which measures speed and length, not
  factual accuracy or biomedical correctness.
- **No NAPLEX / USMLE evaluation set.**
- **No held-out gold-standard datasets** in the repo.
- **No frontend e2e harness** (no Playwright, no Cypress).
- **No DDI evidence citations** (no PMID/DOI link-out, `evidence_level`
  is free-text LLM output).
- **Single secret leaked in version control** ,
  `backend/ecosystem.config.js:9-11` inlines SMTP credentials.

For a paper, the binding/safety/SAR pipeline should be framed as
**reasoning + curation + permutation over external-tool output and
RDKit-derived features**, not as a structure-based discovery engine.
The headline ADMET accuracy claims would need a benchmark harness
built outside this repo before they can be cited.
