# Deep Research Pipeline, Factual Inventory

Source of truth: `backend/app/services/deep_research.py` (3,527
lines), `backend/app/services/research_tasks.py` (786 lines), plus
literature / citation / grounding services. Every claim is anchored
to file + line. "What's solid / partial / missing" at the end calls
out gaps between documented capability and working code.

---

## 1. Pipeline nodes

The agent is a four-node sequential graph orchestrated by
`DeepResearchService.run_research()`
(`backend/app/services/deep_research.py:2521-2649`). The docstring at
line 537 calls it "LangGraph-style" but the implementation is a
hand-rolled state machine with string transitions
(`initializing` → `planning_completed` → `researching_completed` →
`reviewing_completed` → `complete`) and Supabase-backed checkpoints
between phases (`save_checkpoint`/`load_checkpoint`, lines 564-619).

**1.0 Pre-grounding hook.** Before the planner,
`run_research` calls `pre_ground_message(question)`
(`deep_research.py:2573`) to fetch verified RCSB PDB, PubMed,
UniProt, ChEMBL, and DOI metadata. The result lands on
`state.grounded_block` and is injected into both the planner and
writer system prompts (lines 900-908, 1407-1415). Sub-services live
in `backend/app/services/grounding/` (chembl, europepmc, pdb,
pubchem, pubmed, uniprot).

**1.1 Planner** (`_node_planner`, lines 863-947). Mode
`deep_research`; router priority `[GROQ, OPENCODE_GO, POLLINATIONS,
MISTRAL]` (`multi_provider.py:98`). Groq model is
`openai/gpt-oss-120b` (`multi_provider.py:167`); OpenCode Go falls
back to `mimo-v2.5`. JSON mode, `max_tokens=8192`,
`temperature=0.3`. Prompt demands 4-14 sub-topics (≥2 comparative,
≥2 international, ≥1 cross-institutional), 3-5 keywords each, target
~30-50 citations. Output is markdown-fence-stripped, then
`json.loads()`. On `JSONDecodeError` it sets `state.error_message`
and aborts, no retry, no model swap.

**1.2 Researcher** (`_node_researcher`, lines 949-1161). Generates
3 search queries per step via a sub-LLM call (JSON mode, lines
1023-1033). Executes them under `asyncio.Semaphore(3)` concurrency.
Source preference: PubMed (50/query via `ResearchTools.search_pubmed`
at lines 284-429) or Web (10/query via `search_web` → Serper at
431-451). For PubMed hits with a PMCID, attempts PMC full text via
`PMCFullTextService` and falls back to abstract.
`_is_valid_finding` (lines 725-747) filters captchas, 403/404
pages, < 20-char content, missing URLs.

**1.3 Reviewer/Critic** (`_node_reviewer`, lines 1163-1298). Same
mode, JSON. Examines the last 100 findings (3-line summaries, line
1186). Prompt evaluates specificity, mechanistic depth, coverage.
**Hard floor of 10 citations** forces `sufficient=False` regardless
of LLM output (lines 1238-1243). Recursion: if `sufficient=False`
AND `iteration_count < max_iterations` (default 2, line 211),
appends 1 new step (`new_queries[:1]`, line 1282) and re-invokes the
researcher. Citations are built here (lines 1251-1275) by dedupe on
case-insensitive title, copying `_pubmed_data` into a `Citation`
dataclass.

**1.4 Writer** (`_node_writer`, lines 1304-2289). Most of the
pipeline by volume. Two tier-0 → tier-2 fallbacks operate in series.

- **Headers** (lines 1431-1607): `deep_research_elite` mode for 5
  "declarative" H2 headers. Generic-keyword rejection ("mechanisms
  of action", "comparative analysis") triggers a `fast`-mode
  secondary call (line 1568), then keyword-keyed hardcoded
  templates (line 1525), then a final generic fallback (line 1588).
- **Tier 0, map-reduce** (lines 1665-1773). Parallel
  `asyncio.gather(return_exceptions=True)` per section
  (`max_tokens=4000`, temp 0.7); a synthesizer pass
  (`max_tokens=20000`, temp 0.5) stitches them with an executive
  summary and conclusion. `< 2000` chars triggers Tier 1.
- **Tier 1, monolithic elite** (lines 1781-1842).
  `max_tokens=24576`, mode `deep_research_elite` → OpenCode Go
  `deepseek-v4-pro` (`multi_provider.py:256`). Heartbeat task every
  30s emits a `Writing` progress callback so the UI doesn't freeze.
- **Tier 2, Groq Lite** (lines 1846-1905). Top-15 citations,
  `max_tokens=12288`, mode `deep_research_single_pass` → OpenCode Go
  `mimo-v2.5`.

**1.5 Post-write** (lines 1907-2289). Citation extraction (5 regex
patterns, lines 1956-2001), fuzzy author match (lines 2003-2026),
`MIN_CITATIONS=25` backfill (line 2061), supplementary references
(line 2087), topic-coverage diversity (line 2102), drops citations
with missing author/year metadata to prevent the historical
"Unknown. (n.d.)" cascade (lines 2142-2157), APA reference list
(lines 2211-2262), H1 title swap to match `state.original_question`
(lines 2264-2270).

`run_research_streaming` (line 2651+) is explicitly deprecated
("Replaced by background task system"). Production routes through
`BackgroundResearchService._process_task`.

---

## 2. Search backends

Confirmed active in `deep_research.py`:

1. **PubMed E-utilities**, `search_pubmed` (lines 284-429). Manual
   `esearch` + `efetch` XML parse for title/abstract/DOI/PMCID/
   authors/journal/year. Retry chain `[5s, 15s, 30s]` with timeout
   escalation 15s→25s.
2. **Serper (Google Scholar)**, `search_web` (lines 431-451) via
   `app.services.serper.SerperService`. No PMC enrichment, no
   full-text fetch.
3. **PMC full text**, `PMCFullTextService` (lazy property at lines
   249-255) for PubMed results carrying a PMCID.

Referenced elsewhere in the repo but **not invoked from the
deep-research pipeline**:
- `literature_service.py` aggregates PubMed + Semantic Scholar via
  `search_all` (lines 40-77) and resolves OA PDFs through Semantic
  Scholar → Unpaywall → PubMed (lines 79-180). Grep for
  `literature_service` in `deep_research.py` returns 0 hits.
- `citation_service.py` resolves DOIs via CrossRef and PMIDs via
  PubMed ESummary (lines 36-113). Not invoked from deep research.

Documented in CLAUDE.md / Rule 19 but **absent in code**: OpenAlex,
DuckDuckGo, arXiv/bioRxiv/medRxiv API search. The biorxiv/medrxiv/
arxiv strings exist only as trusted-domain whitelists in PDF URL
validators (`literature_service.py:98`,
`semanticscholar_service.py:23-24`). Rule 19's chain ("Semantic
Scholar → PubMed → DuckDuckGo → empty graceful") describes
something other than this pipeline; deep research's actual chain is
**PubMed → Serper → empty**.

Rate-limit handling: PubMed retries 3× with backoff
(lines 289-291); Semantic Scholar returns `[]` on HTTP 429
(`semanticscholar_service.py:77-79`) with no retry; Serper errors
are swallowed (`deep_research.py:449-451`).

---

## 3. Citation handling

Construction is a single locus at lines 1250-1275: dedupe by
case-insensitive title only, DOI/PMID dedupe is **not** applied
inside deep research even though `_extract_doi` exists (line 273).
Each finding stashes a `_pubmed_data: Dict` (line 184); reviewer
copies that into a `Citation` dataclass.

**Rule 34 (live-state mutation in checkpoints), VERIFIED CLEAN.**
`save_checkpoint` (lines 564-598) defines a local `_scrub` helper
operating on `asdict(state)` (a deep copy). The historical bug
pattern `for f in state.findings: f._pubmed_data = {}` is no longer
present anywhere; `grep -n "for f in state.findings"
deep_research.py` returns only the citation-build read loop at line
1252.

Citation renumbering (lines 2159-2183) uses Pydantic
`model_copy(update={"id": ...})` (or `copy.copy` fallback) to make
fresh objects, leaving `state.citations` untouched. Inline comment
documents the "fix it, regress after checkpoint reload" cycle this
prevents.

Author-name normalization across sources is minimal, Semantic
Scholar's `Last, F.` form would collide with PubMed's `Last, FM`
form if they were merged, but they aren't on this path.

---

## 4. Hallucination mitigation

**No claim-level evidence validation against source PDFs or
abstracts is performed.** This is the single largest gap.

`backend/app/services/evidence_validator.py` exists (142 lines) but
is **dead code**. `grep -rn "EvidenceValidator" backend/app/`
returns only the class definition plus its test file. It is not
imported by `deep_research.py`, `research_tasks.py`,
`multi_provider.py`, `ai.py`, or the container. Inspection
(lines 21-142) shows the class scores abstracts on study-design
hierarchy (meta-analysis 5pts, RCT 4pts, observational 3pts...),
extracts `n=X` sample sizes via regex, and flags `p<0.05`
statements. It does not check claims against sources.

What IS present:

- **Prompt-level anti-hallucination directives.** Planner forbids
  inventing PDB/PMID/DOI/UniProt/ChEMBL IDs not in
  `<grounded_facts>` (lines 900-908). Writer says the same and
  instructs the model to emit "verification needed" when uncertain
  (lines 1410-1415). Writer Rule 10 demands exact-match author
  surnames from GROUNDING DATA (line 1385).
- **Post-hoc in-text citation filter** (lines 2028-2057). Extracts
  `(Author, Year)` patterns from the report, keeps only `Citation`
  objects whose authors string contains a matching surname AND
  matching year, with `difflib.SequenceMatcher` ≥ 0.85 fuzzy
  threshold. This drops *hallucinated citations* from the reference
  list, if the model wrote `(Smith, 2024)` and no real Smith-2024
  exists in `state.citations`, that citation falls out.
- **Metadata floor** (lines 2142-2157). Drops references whose
  authors OR year is empty/`"unknown"` to prevent "Unknown. (n.d.)"
  cascades.

What is NOT done: no second pass fetches the cited PDF/abstract and
asks "does this claim appear in this source?" There is no NLI, no
semantic similarity check, no QA-over-context check. A model can
correctly cite paper #14 but attribute a fact paper #14 never made;
the pipeline cannot detect this. Mapping the task's criteria:
**(a) source-text presence**, only as PMC retrieval gate, not for
claim checking; **(b) similarity threshold**, only for author
dedup, not for claim-source alignment; **(c) explicit "no evidence"
labelling**, only as a prompt request to the LLM, with no
programmatic enforcement.

---

## 5. Output format

Sections (writer prompt, lines 1366-1401):

```
# {research_question}
## Executive Summary
## {LLM-generated declarative header 1..5}
## Conclusion and Future Directions
## References          ← appended programmatically (lines 2257-2262)
```

Length budget per system prompt: 4,000-5,000 words (line 1361); per
user prompt: 4,500-6,000 (line 1651). A body under 5,000 chars
(~1,250 words) is detected at line 1926 and replaced with an
explicit error message (line 1933).

References: APA 7th, alphabetised by first-author surname
(`format_apa_citation`, lines 2211-2261). Includes journal italics,
volume/issue/pages, DOI/PMID/URL fallback chain.

**Token budgets (verified by grep on `max_tokens`):** planner 8192,
researcher sub-LLM 8192, critic 8192, writer Tier 0 sections 4000,
Tier 0 synthesizer 20000, Tier 1 monolithic **24576**, Tier 2
fallback 12288, clarifying questions 2000. CLAUDE.md claims the
writer gets 8K, the codebase actually passes 24,576. CLAUDE.md is
stale on this point.

---

## 6. Streaming (SSE)

`progress_callback(step_name, details)`, `step_name` ∈
`{Planning, Researching, Reviewing, Writing, Resuming}`. `details`
may be a raw string or a JSON string carrying
`sub_type ∈ {plan_complete, step_start, step_complete}`. The Living
Document `phases` array is assembled in `research_tasks.py:330-436`
with `status ∈ {pending, active, completed, failed}`.

**Rule 15 / "step phases stuck spinning" fix, VERIFIED IN CODE.**
`process_step` (`deep_research.py:974-1126`) wraps the search body
in `try/except/finally`. The `finally` block (lines 1101-1118)
ALWAYS emits `step_complete` with `status` set to `completed` or
`failed` and an `error` field on failure. Outer
`asyncio.gather(*tasks, return_exceptions=True)` (line 1135) is the
belt-and-braces guarantee. `research_tasks.py:391-402` honours the
incoming `status` so a failed step doesn't render green. Frontend
`useChatState.ts:30` types the status union including `'failed'`;
`DeepResearchUI.tsx:90,100` renders rose AlertCircle + error text
for failed phases.

Heartbeat tasks (lines 1788-1797, 1873-1882) emit every 30s during
writer calls. SSE transport at
`backend/app/api/v1/endpoints/ai.py:1032-1334`
(`/deep-research/stream`) polls Supabase `research_tasks` every 2
seconds (line 1178), emits
`progress`/`status`/`heartbeat`/`complete`/`error`, and falls back
to a 15-second connection heartbeat (line 1134).

---

## 7. PDF generation + email delivery

`BackgroundResearchService._process_task` calls
`generate_research_pdf` at `research_tasks.py:651`. Implementation
at `deep_research.py:2840+` uses `xhtml2pdf.pisa`.

**Rule 33 / `clean_unicode_for_pdf(None)` crash, VERIFIED FIXED.**
Lines 2897-2907:

```python
def clean_unicode_for_pdf(text: str) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
```

Plus an empty-content guard at line 2865 that raises
`ValueError("report_content is empty")` before rendering. Inline
comment 2898-2903 documents the historical crash.

Retry-once pattern at `research_tasks.py:649-664`, generate the
PDF up to 2× before the fallback branch. The fallback path at
`research_tasks.py:735-743` calls
`email_service.send_research_completed_email(..., pdf_failed=True)`,
whose copy (`email.py:283-320`) honestly tells the user the
attachment is unavailable and points them to the in-app report.

Email opt-in: honours `notify_by_email` from task metadata (default
`True`, line 616), set at task creation from the frontend checkbox
(`ai.py:1322`). Subject line is `\n`/`\r`-stripped for SMTP
compliance (`research_tasks.py:673`).

---

## 8. NAPLEX evaluation

**None found.** `grep -rn "NAPLEX\|naplex\|North American
Pharmacist" /Users/mac/Desktop/phhh/` returns zero matches across
backend, frontend, tests, scripts, docs, kiro context, notes. No
NAPLEX question bank, no evaluation script, no accuracy log, no
benchmark file. If such an evaluation was performed it lives
outside this repo.

---

## 9. Citation faithfulness measurement

**None found.** No harness fetches each claim's cited source and
verifies the claim. The closest artefact is
`_verify_citation_density` at `deep_research.py:753-776` which
counts unique citations and citations per paragraph, a *density*
metric, not *faithfulness*. `grep -rn "faithfulness\|
citation_faithfulness\|claim_verification" backend/` returns zero.
The dead-code `EvidenceValidator` scores study-design strength, not
claim-source alignment.

---

## 10. Background task user context (Rule 31)

`BackgroundResearchService._process_task` is the only background
path into the pipeline. At `research_tasks.py:452` it passes
`UUID(user_id)` to `run_research(user_id=...)`. The deep-research
service never uses the value beyond a debug log; it does NOT call
`chat_service.add_message(msg, user=User)` from the background
worker. The user_id is used only at line 459 (to fetch the email
address from the `users` table) and at line 492 (to call
`chat_service.create_response_branch(user_message_id=...)`, whose
signature at `chat.py:1041` accepts a UUID, not a `User` model).

So Rule 31 is moot for this pipeline: passing a raw UUID is correct
because `add_message` is never invoked by the background worker ,
the branch path uses `user_message_id` lookup instead.

---

## 11. Branch activation (Rule 32)

**VERIFIED.** `research_tasks.py:492-525` calls
`chat_service.create_response_branch(user_message_id=...,
content=state.final_report,
model_used="deep_research_elite", metadata={...})`. The metadata
payload includes `mode: "deep_research"`, `task_id`,
`citations_count`, `phases`, and the full `citations` list
(id/title/authors/source/url/doi/pmid/year per item).

`chat.create_response_branch` (`chat.py:1041-1194`) populates
`assistant_responses` + branch labels (A, B, C...), with
duplicate-prevention by task_id (lines 1048-1106) so a re-stream
updates the existing branch instead of creating a duplicate. The
`user_message_id` is taken from task metadata
(`research_tasks.py:467`) with a fallback finding the latest
user-role message (lines 471-481). If neither resolves, the branch
is skipped and logged at line 553.

---

## 12. Tests

**`tests/regression/test_literature.py`** (125 lines):
`search_all` authors-as-list shape; 6+ `is_likely_pdf_url` valid
cases (arxiv, biorxiv, pmc, researchsquare, .pdf suffix,
doi.org); invalid cases (Nature/Springer .pdf, HTML landing,
None); Semantic Scholar OA URL round-trip.

**`tests/regression/test_literature_pdf.py`** (53 lines):
`fetch_pdf_bytes` 403/404/200 paths.

**`tests/test_evidence_validator.py`** (93 lines): study-type,
sample-size, p-value, quality score. Tests pass; class is never
invoked in production.

**`tests/test_citation_service.py`** (414 lines): CrossRef DOI and
PubMed PMID resolution + APA/Vancouver/BibTeX formatting. Service is
wired into chat/RAG, not into deep research.

**Not tested:** planner JSON schema validation; reviewer hard-floor
enforcement; writer Tier 0 → 1 → 2 fallback transitions; the 5
citation regex patterns and fuzzy-match author logic;
`MIN_CITATIONS=25` backfill; `_has_usable_metadata` "Unknown.
(n.d.)" filter; end-to-end `run_research` flow with
checkpoint save/load; `process_step` failed-event contract;
`clean_unicode_for_pdf(None)` None-safety; the
`create_response_branch` integration; the pre-grounding hook's
effect on planner/writer prompts.

---

## What's solid

- Four-node graph with Supabase-backed checkpoints between every
  node; recovery from worker restart mid-Researching.
- Step-level fault tolerance: `try/except/finally` +
  `asyncio.gather(return_exceptions=True)` guarantees every step
  emits `step_complete`.
- Live-state mutation in checkpoints (Rule 34) is solidly fixed ,
  `_scrub` operates on a deep copy; the historical mutation pattern
  is absent.
- PDF None-safety (Rule 33), None/non-str guards in
  `clean_unicode_for_pdf`, empty-body `ValueError`, retry-once,
  honest `pdf_failed=True` fallback email copy.
- Branch activation (Rule 32) through `create_response_branch` with
  task-id deduplication.
- Citation hallucination filter, 5-regex extraction + fuzzy author
  + year match (`SequenceMatcher ≥ 0.85`) drops in-text citations
  the model invented.
- Pre-grounding hook wires verified PDB/PMID/UniProt/ChEMBL/DOI
  metadata into both planner and writer prompts.

## What's partial

- Reviewer is single-pass and recursion-capped at 2 rounds with 1
  new query per round, limited gap-fill capacity.
- Search fan-out is narrower than the README claims: deep research
  uses **PubMed + Serper Google Scholar** only. Semantic Scholar,
  CrossRef, OpenAlex, arXiv, bioRxiv, medRxiv, DuckDuckGo are
  not invoked from this pipeline despite being documented as part
  of the fallback chain.
- Citation dedup is title-only; no DOI/PMID dedup within deep
  research.
- Token budget documentation is stale: CLAUDE.md says writer gets
  8K; code passes 24,576.
- Header-generation fallback silently degrades to generic templates
  when both LLM tiers fail, contradicting the prompt's own ban on
  generic headers.

## What's missing

- **NAPLEX evaluation**: not in this repo. Zero hits.
- **Citation faithfulness / claim-source verification**: no harness
  fetches the cited source and checks whether it supports the claim.
- **Programmatic "no evidence" labelling**: prompts ask for
  "verification needed" but nothing detects unsupported claims or
  inserts `[unverified]` markers.
- `EvidenceValidator` is **dead code**, defined and tested, never
  imported. Its 142 lines score study-design strength, not claim
  alignment.
- DuckDuckGo / OpenAlex / arXiv / bioRxiv / medRxiv API search not
  implemented.
- No top-level "single-pass" entry point;
  `deep_research_single_pass` mode is only reached as the Tier 2
  fallback inside `_node_writer`.
- End-to-end regression tests for the planner/researcher/reviewer/
  writer chain. The 190-test claim in CLAUDE.md covers other
  surfaces; deep research is exercised only at the
  literature-URL-validation layer.
- Semantic Scholar wiring into deep research, the service exists
  and works but `ResearchTools` does not call it.

The pipeline is structurally sound for retrieval + generation with
defence-in-depth on the most painful historical failure modes
(spinning steps, checkpoint mutation, empty PDFs, hallucinated
in-text citations). It is structurally absent on claim-level fact
verification: writer outputs are trusted to the extent that the
model cites real papers, but no programmatic check ever confirms
the paper actually contains the claimed fact.
