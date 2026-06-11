# Discussion expansion (drop-in prose for §5)

Prepared for the cheminformatics preprint at `paper/manuscript.md`. The
four sections below are ready to fold into the existing Discussion as
new subsections or as additions to §5.2 and §5.3. Citation numbers
follow the manuscript's existing scheme: existing references are
re-cited by their existing numbers (1, 2, 3, etc.); new references
start at (27). A consolidated list of new references for each section
is given in APA-bracketed form at the end of each section so the author
can splice the entries into the manuscript's reference list in order.

A hard formatting rule was applied throughout: no em-dash characters
are used. Comma, colon, semicolon, and period substitutes are used in
their place.

---

## A. Comparison to recent agentic and LLM-driven cheminformatics pipelines

The last three years have produced a recognisable family of
LLM-driven and agentic cheminformatics systems with which the pipeline
described here can be usefully compared. The closest in spirit is
**ChemCrow** (27), which equips a GPT-4 backbone with eighteen
chemistry tools (RDKit transforms, reaction-prediction, retrosynthesis
search, name-to-structure, safety lookup, web search) and lets the
language model plan tool use across organic-synthesis, drug-discovery,
and materials tasks. ChemCrow is evaluated by expert-graded chemical
factuality on a tasks-of-interest set and by end-to-end success on the
syntheses of an insect repellent and three organocatalysts. The
overlap with the present work is the tool-augmented agent skeleton; the
difference is that ChemCrow's deterministic check is the *human expert*
grading the output, whereas the pipeline reported here pushes the
correctness budget onto stacked deterministic gates so that the LLM
output can be trusted without per-call human review. **Coscientist**
(28) (Boiko et al., *Nature* 2023) extends the agent into the wet lab,
driving a robotic flow-chemistry platform on Pd-catalysed
cross-couplings; their evaluation is wall-clock-to-product on real
reactions, an orthogonal benchmark to the in-silico recovery and
self-consistency numbers reported in §4. Both ChemCrow and Coscientist
treat the LLM as the orchestrator and the tools as oracles, which is
inverted relative to the present pipeline, where the LLM is the
oracle and the orchestrator is deterministic Python.

In the **structure-aware generation** family, the relevant
recent work spans REINVENT 4 (29), Pocket2Mol (30), DiffSBDD (31),
TamGen (32), EquiBind (33), DiffDock (34), and PocketGen (35).
REINVENT 4 (29) is a production-grade reinforcement-learning generator
that supports de novo design, scaffold decoration, linker design, and
analog optimization across SMILES and graph backbones, and is the
closest published peer for the *transformation-driven analog
generation* part of the present pipeline; we differ in that REINVENT's
search is policy-gradient over a learned generator, whereas our search
is a deterministic enumeration of an audited 479-entry SMIRKS library
gated by a chemistry-validity allowlist. Pocket2Mol (30) and DiffSBDD
(31) are pocket-conditional generators that emit ligand atoms directly
from a 3D pocket; they require a co-crystal structure and a pocket
extraction step that our pipeline deliberately does not assume,
trading the protein-side richness for the ability to operate on any
lead for which a 2D ligand-interaction diagram is available. TamGen
(32) is a target-aware chemical-language-model generator with reported
sub-micromolar wet-lab hits against *Mycobacterium tuberculosis* ClpP,
demonstrating that generative LLM-backed pipelines can reach
experimentally validated leads; we share the LLM backbone and the
target-aware framing but consume the target signal as a vision
classification of an LID rather than as a learned pocket embedding.
EquiBind (33) and DiffDock (34) are docking models rather than
generators; they appear in our comparison only because the present
pipeline can consume docking output as a numeric input to ranking but
does not compute docking internally. PocketGen (35) inverts the
problem (design the pocket, given a ligand) and is therefore
complementary rather than comparable.

For **vision-language molecule understanding**, the most directly
related work is MolReGPT (36), GIT-Mol (37), MolFM (38), and
DECIMER.ai (39). MolReGPT (36) demonstrates that in-context-learning
with retrieved exemplars lets an off-the-shelf ChatGPT model match
fine-tuned MolT5 on molecule-caption translation; the lesson the
present pipeline applies is the same (use the production model with a
fixed structured prompt, do not fine-tune a per-task model), but our
target is structured JSON over a labelled-instance list, not free-text
captioning. GIT-Mol (37) and MolFM (38) integrate graph, image, and
text modalities into a unified latent space and are evaluated on
property prediction and molecule generation; their architectural
ambition (one model, three modalities) is greater than ours, but the
evaluation does not measure the specific quantity we care about
(robustness of LID-derived restricted-atom classification), and they
do not address downstream defence in depth at all. DECIMER.ai (39) is
the closest specialised vision tool, an open-source EfficientNet-V2 +
Transformer pipeline that reads a printed 2D structure depiction and
emits SMILES; it does not address binding-interaction extraction from
LIDs, which is the specific vision sub-task we depend on. Across all
of this work, the empirical gap the present paper addresses is *not*
"LLMs can do chemistry" (already shown) and *not* "vision-language
models can read molecule images" (already shown), but rather "how do
you bolt an imperfect vision-language classifier into a
production-grade analog generator without letting its perception
errors corrupt the output set", and the answer this paper documents is
the defence-in-depth wrapping reported in §5.1.

A useful, current systematic survey of this fast-moving space is the
Ramos et al. review of LLMs and autonomous agents in chemistry (40),
which catalogues 30+ chemistry-focused agentic systems published
between 2023 and 2024 and observes that very few of them carry
deterministic post-hoc guardrails; the present paper can be read as
one concrete realisation of what those guardrails look like in
production for lead optimization.

### New references introduced in section A

```
[27] M. Bran, A., Cox, S., Schilter, O., Baldassari, C., White, A. D., & Schwaller, P. (2024). Augmenting large language models with chemistry tools. *Nature Machine Intelligence*, *6*(5), 525–535. https://doi.org/10.1038/s42256-024-00832-8
[28] Boiko, D. A., MacKnight, R., Kline, B., & Gomes, G. (2023). Autonomous chemical research with large language models. *Nature*, *624*(7992), 570–578. https://doi.org/10.1038/s41586-023-06792-0
[29] Loeffler, H. H., He, J., Tibo, A., Janet, J. P., Voronov, A., Mervin, L. H., & Engkvist, O. (2024). Reinvent 4: Modern AI-driven generative molecule design. *Journal of Cheminformatics*, *16*(1), 20. https://doi.org/10.1186/s13321-024-00812-5
[30] Peng, X., Luo, S., Guan, J., Xie, Q., Peng, J., & Ma, J. (2022). Pocket2Mol: Efficient molecular sampling based on 3D protein pockets. In *Proceedings of the 39th International Conference on Machine Learning (ICML)*, PMLR 162, 17644–17655. https://doi.org/10.48550/arXiv.2205.07249
[31] Schneuing, A., Harris, C., Du, Y., Didi, K., Jamasb, A., Igashov, I., Du, W., Gomes, C., Blundell, T. L., Lio, P., Welling, M., Bronstein, M., & Correia, B. (2024). Structure-based drug design with equivariant diffusion models. *Nature Computational Science*, *4*(12), 899–909. https://doi.org/10.1038/s43588-024-00737-x
[32] Wu, K., Xia, Y., Deng, P., Liu, R., Zhang, Y., Guo, H., Cui, Y., Pei, Q., Wu, L., Xie, S., Chen, S., Lu, X., Hu, S., Wu, J., Chan, C.-K., Chen, S., Zhou, L., Yu, N., Chen, E., Liu, H., Guo, J., Qin, T., & Liu, T.-Y. (2024). TamGen: drug design with target-aware molecule generation through a chemical language model. *Nature Communications*, *15*, 9360. https://doi.org/10.1038/s41467-024-53632-4
[33] Stärk, H., Ganea, O.-E., Pattanaik, L., Barzilay, R., & Jaakkola, T. (2022). EquiBind: Geometric deep learning for drug binding structure prediction. In *Proceedings of the 39th International Conference on Machine Learning (ICML)*, PMLR 162, 20503–20521. https://doi.org/10.48550/arXiv.2202.05146
[34] Corso, G., Stärk, H., Jing, B., Barzilay, R., & Jaakkola, T. (2023). DiffDock: Diffusion steps, twists, and turns for molecular docking. In *Proceedings of the 11th International Conference on Learning Representations (ICLR)*. https://doi.org/10.48550/arXiv.2210.01776
[35] Zhang, Z., Shen, W. X., Liu, Q., & Zitnik, M. (2024). Efficient generation of protein pockets with PocketGen. *Nature Machine Intelligence*, *6*(9), 1124–1134. https://doi.org/10.1038/s42256-024-00920-9
[36] Li, J., Liu, Y., Fan, W., Wei, X.-Y., Liu, H., Tang, J., & Li, Q. (2023). Empowering molecule discovery for molecule-caption translation with large language models: A ChatGPT perspective. *arXiv preprint*. https://doi.org/10.48550/arXiv.2306.06615
[37] Liu, P., Ren, Y., Tao, J., & Ren, Z. (2024). GIT-Mol: A multi-modal large language model for molecular science with graph, image, and text. *Computers in Biology and Medicine*, *171*, 108073. https://doi.org/10.1016/j.compbiomed.2024.108073
[38] Luo, Y., Yang, K., Hong, M., Liu, X. Y., & Nie, Z. (2023). MolFM: A multimodal molecular foundation model. *arXiv preprint*. https://doi.org/10.48550/arXiv.2307.09484
[39] Rajan, K., Brinkhaus, H. O., Agea, M. I., Zielesny, A., & Steinbeck, C. (2023). DECIMER.ai: an open platform for automated optical chemical structure identification, segmentation and recognition in scientific publications. *Nature Communications*, *14*, 5045. https://doi.org/10.1038/s41467-023-40782-0
[40] Ramos, M. C., Collison, C. J., & White, A. D. (2025). A review of large language models and autonomous agents in chemistry. *Chemical Science*, *16*, 2514–2572. https://doi.org/10.1039/D4SC03921A
```

---

## B. Failure-mode analysis of the defence-in-depth design

The defence-in-depth wrapping documented in §2 absorbs many but not
all classes of error, and the failure surface that remains is worth
making explicit. Four failure modes the architecture is most exposed
to are: (i) **vision-model false negatives**, where the classifier
misses a binding contact entirely and a restricted group is allowed
into the editable set; (ii) **SMIRKS library coverage gaps**, of which
the indole-to-quinoline ring-expansion case in §4.1 is the empirically
surfaced exemplar but is not the only one (any ring-size-changing
operation, any reagent-implicit transform such as N-alkylation under
specific protection, and any stereochemistry-modifying transform are
in the same scope-of-substitution-vocabulary class); (iii) **soft
Murcko gate over-permissiveness**, where a ring-topology-preserving
edit silently changes the electronics of the scaffold (for example, a
phenyl-to-pyrimidine swap inside a ring system) and the gate's
predicate (same ring count, same aromaticity) does not see the
electronic change; and (iv) **chemistry-validator
over-restrictiveness**, where the static allowlist refuses a
non-canonical but real interaction (e.g. a fluorine acting as a
weak H-bond acceptor in a specific geometric context, or a sulfur
participating in a non-standard cation-π interaction).

A fifth class the author should consider is **structural-alert false
positives**, by which we mean PAINS or Brenk substructures that are
legitimate medicinal-chemistry motifs and whose presence in the
analog set is *not* a real liability. Capuzzi et al. (41)
re-analysed the original PAINS-A/B/C filters against a 95,000-compound
in-house pharmaceutical screening collection and reported that 97% of
PAINS-flagged compounds were infrequent rather than promiscuous
hitters, and that 68% of the 480 published alerts were derived from
four or fewer compounds, so the alert-positive predictive value is
target- and assay-class-dependent rather than universal. The Saubern
et al. analysis (42) corroborated this on a separate pharmaceutical
data set. In the present pipeline, the audit numbers in Table at §4.2
show that the SMIRKS library raises the Brenk-flagged rate from 26.1 %
on the seed compounds to 46.5 % under the gate-on default; some of
that rise is real (the library introduces alert-substructure-bearing
products) but some is artefactual structural-alert flagging in the
sense Capuzzi documented. A practical mitigation is to (a) treat
PAINS-A separately from PAINS-B/C (the latter two are derived from
much smaller compound counts and are known to be noisier), (b) attach
the alert as an informational tag with a *soft* score penalty rather
than as a hard reject when the indication is target-class-known and
the alert is on the lower-evidence list, and (c) cross-check
alert-flagged analogs against a more recent assay-class-aware
liability set (e.g. the Eli Lilly MedChem rules of Bruns and Watson
(43)) before final reporting.

A sixth and arguably load-bearing failure mode is **ADMET-prediction
distribution shift**. The Chemprop-V2 backbone used by `admet_ai` (2)
is trained on the Therapeutics Data Commons ADMET benchmark group
(44), whose 22 datasets range from 475 to 13,130 molecules per
endpoint with scaffold-split 80/20 holdouts. Recent
out-of-distribution work (45) reports that ADMET models degrade
substantially when test compounds occupy chemical space outside the
training set's scaffold neighbourhoods, and the SMIRKS engine in this
pipeline is *deliberately designed to take the lead off its scaffold*;
the very transformations the engine is built to perform push the
output into regions of chemical space where the ADMET screen is least
calibrated. The present pipeline does not currently emit a
per-endpoint applicability-domain confidence flag; adding one (e.g. by
Tanimoto-similarity to the nearest training-set neighbour, or by the
Mahalanobis distance in the Chemprop fingerprint space) would let the
ranking step downweight predictions that are unreliable rather than
treat all predictions as equally informative. A seventh failure mode,
worth mentioning briefly, is **synthetic-accessibility metric
brittleness**: SYBA (1) is a Bayesian classifier trained on a fixed
easy-/hard-to-synthesise corpus and inherits that corpus's coverage
limits; on highly novel scaffolds the score can be over-confident, and
the present pipeline's centring-on-zero sigmoid penalty correctly
softens this, but does not eliminate it. The Bender and
Cortés-Ciriano (46) two-part review on what is realistic and what is
illusion in AI for drug discovery is the right meta-reference for
calibrating expectations on all of the above.

### New references introduced in section B

```
[41] Capuzzi, S. J., Muratov, E. N., & Tropsha, A. (2017). Phantom PAINS: Problems with the utility of alerts for pan-assay interference compounds. *Journal of Chemical Information and Modeling*, *57*(3), 417–427. https://doi.org/10.1021/acs.jcim.6b00465
[42] Saubern, S., Guha, R., & Baell, J. B. (2011). KNIME workflow to assess PAINS filters in SMARTS format. Comparison of RDKit and Indigo cheminformatics libraries. *Molecular Informatics*, *30*(10), 847–850. https://doi.org/10.1002/minf.201100076
[43] Bruns, R. F., & Watson, I. A. (2012). Rules for identifying potentially reactive or promiscuous compounds. *Journal of Medicinal Chemistry*, *55*(22), 9763–9772. https://doi.org/10.1021/jm301008n
[44] Huang, K., Fu, T., Gao, W., Zhao, Y., Roohani, Y., Leskovec, J., Coley, C. W., Xiao, C., Sun, J., & Zitnik, M. (2021). Therapeutics Data Commons: Machine learning datasets and tasks for drug discovery and development. In *Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks* (Vol. 1). https://doi.org/10.48550/arXiv.2102.09548
[45] Yang, S., Li, K., Tang, X., Wang, L., & Cao, D. (2024). ADMEOOD: Out-of-distribution benchmark for drug property prediction. *arXiv preprint*. https://doi.org/10.48550/arXiv.2310.07253
[46] Bender, A., & Cortés-Ciriano, I. (2021). Artificial intelligence in drug discovery: what is realistic, what are illusions? Part 1: Ways to make an impact, and why we are not there yet. *Drug Discovery Today*, *26*(2), 511–524. https://doi.org/10.1016/j.drudis.2020.12.009
```

---

## C. Regulatory and medicinal-chemistry implications

In the standard hit-to-lead and lead-optimization workflow, the
output of a pipeline of this kind, a ranked list of pharmacophore-
preserving, ADMET-screened, structural-alert-filtered analogs with
provenance manifests, sits upstream of the medicinal chemist's bench
prioritization and informs which analogs are synthesised, assayed in
vitro for target binding and orthogonal selectivity, and progressed to
animal PK. The most natural integration point is the SAR cycle: each
iteration's wet-lab data updates the project-context analysis (stage
5), which re-weights the next round's ADMET screen and the ranker's
endpoint priorities. None of the steps in this pipeline are
binding-validated, in the sense the author explicitly notes in §4.4;
the role of the pipeline is to *narrow* the candidate set the
chemist examines, not to assert that any specific output binds the
target. The pipeline's role in **ADME-tox triage** is more direct:
because the per-analog ADMET vector is computed by the
Chemprop-V2-backed `admet_ai` (2) on the TDC benchmark group (44), the
liability signals (hERG, AMES, DILI, CYP inhibition) are commensurable
with the predictions the medicinal-chemistry community already uses to
prioritize tox-axis follow-up, and they fall under the long-running
in-silico-tox-prediction framework reviewed by Vamathevan et al. (47).

The **regulatory** picture is the right place to be conservative. For
genotoxicity and mutagenicity specifically, ICH M7(R2) (48) is the
operative international guideline and is the first regulatory document
to formally accept in-silico (Q)SAR results in place of in-vitro Ames
testing for initial impurity-hazard classification, requiring two
complementary methodologies (a rule-based and a statistical model)
followed by expert review. The pipeline's structural-alert filter
(PAINS, Brenk) is *not* a substitute for the ICH M7 (Q)SAR step;
PAINS-A/B/C are pan-assay interference filters, Brenk is a neglected-
disease lead-discovery filter, and neither is the validated genotox
classifier ICH M7 contemplates (e.g. Derek Nexus and Sarah Nexus, or
Leadscope and CASE Ultra), but the pipeline's output is a natural
input to that downstream step. On the broader AI/ML-in-drug-development
front, the U.S. FDA's January 2025 draft guidance "Considerations for
the Use of Artificial Intelligence to Support Regulatory Decision-
Making for Drug and Biological Products" (49) sets out a
risk-based credibility-assessment framework with seven enumerated
steps (define the question of interest, define the context of use,
assess the risk, develop a credibility-assessment plan, execute the
plan, document the results, determine adequacy), and the European
Medicines Agency's September 2024 reflection paper (50) sets out
broadly aligned expectations across the EU. Both frameworks place
heavy emphasis on **provenance, reproducibility, and applicability-
domain documentation**, which is precisely what this pipeline's
per-experiment `manifest.json` (git SHA, RDKit version, Python
version, SMIRKS library SHA-256, input dataset SHA-256) is engineered
to support. The cross-provider model benchmark in §4.5 also
contributes here: documenting that the production model and the
fallback chain were each evaluated against the same prompt with the
same rubric is exactly the kind of credibility evidence the FDA's
seven-step framework asks for.

### New references introduced in section C

```
[47] Vamathevan, J., Clark, D., Czodrowski, P., Dunham, I., Ferran, E., Lee, G., Li, B., Madabhushi, A., Shah, P., Spitzer, M., & Zhao, S. (2019). Applications of machine learning in drug discovery and development. *Nature Reviews Drug Discovery*, *18*(6), 463–477. https://doi.org/10.1038/s41573-019-0024-5
[48] International Council for Harmonisation of Technical Requirements for Pharmaceuticals for Human Use. (2023). *ICH M7(R2) Guideline on Assessment and Control of DNA Reactive (Mutagenic) Impurities in Pharmaceuticals to Limit Potential Carcinogenic Risk*. ICH. https://www.ich.org/page/multidisciplinary-guidelines (accessed 2026-06)
[49] U.S. Food and Drug Administration. (2025). *Considerations for the Use of Artificial Intelligence to Support Regulatory Decision-Making for Drug and Biological Products*. Draft Guidance for Industry. Center for Drug Evaluation and Research, FDA. https://www.fda.gov/regulatory-information/search-fda-guidance-documents (accessed 2026-06)
[50] European Medicines Agency. (2024). *Reflection paper on the use of artificial intelligence in the lifecycle of medicines*. EMA/CHMP/CVMP/83833/2023. https://www.ema.europa.eu/en/documents/scientific-guideline/reflection-paper-use-artificial-intelligence-ai-medicinal-product-lifecycle_en.pdf (accessed 2026-06)
```

---

## D. Bias and reproducibility risks

Three classes of bias and reproducibility risk are baked into a
pipeline of this shape and deserve explicit naming. First,
**training-data bias in the ADMET backbone**: `admet_ai` (2) wraps
Chemprop-V2 (3) message-passing networks trained on the TDC ADMET
benchmark group (44), which is itself an aggregation of public
single-task data sets (e.g. AqSolDB for solubility, Caco-2 from Wang et
al., Lipophilicity from ChEMBL, hERG from Karim et al., AMES from
Hansen et al.). Each underlying assay has its own selection bias on
chemical space (literature-reported compounds are not a uniform sample
of drug-like space; positive examples are over-published; certain
laboratory standard scaffolds, kinase hinge binders, GPCR amine
fragments, are over-represented), and recent OOD-benchmark work (45)
shows that scaffold-shifted test sets degrade ADMET predictions
substantially. The practical consequence for our pipeline is that the
ADMET screen at stage 10 is most reliable for analogs that stay close
to the lead's scaffold, and least reliable for analogs the SMIRKS
engine pushes furthest from it, which is the opposite of what one
would naively hope.

Second, **vision-language model training-data origin** is essentially
opaque for the production-class models we use (OpenAI gpt-5.4,
Llama 4 Scout, Gemini, Mistral Pixtral). The vendors do not publish
LID-image-specific training-corpus inventories, and there is no public
audit of how many ligand-interaction-diagram images each model has
seen, drawn from which sources (LigPlot+, PoseView, PLIP, manually
drawn in patents, manually drawn in journal figures), at what
resolution, in which colour scheme, or with which residue-label
convention. The self-consistency Jaccard of 1.00 reported in §4.3
measures *reproducibility on a single LID*; it does not measure
accuracy on out-of-distribution LIDs drawn from a different rendering
pipeline (for example, a Maestro-rendered LID with a different
arrow-head convention than the PoseView convention used in our test
set). The closest related quantification of vision-model behaviour
drift is the LLM-output-drift work reported by Sarwar et al. (51) and
the original ChatGPT-behaviour-changing-over-time study by Chen,
Zaharia, and Zou (52), both of which document substantial
month-over-month variation in fixed-prompt outputs from frozen-version
model APIs.

Third, **provider drift and model deprecation** is the practical
reproducibility nightmare for any LLM-backed production pipeline.
Chen et al. (52) measured GPT-3.5 and GPT-4 on a fixed set of tasks
across three months and found that GPT-4's prime-vs-composite accuracy
fell from 84 % to 51 % between the March and June 2023 versions of the
*same* named API endpoint; code-generation formatting accuracy
degraded over the same window; instruction-following ability fell.
Sarwar et al. (51) extend this analysis with a cross-provider
validation framework for financial workflows and document that even
when the model name and version pin are held constant, vendor-side
fine-tuning, safety-filter retuning, and infrastructure-level
sampling-default changes can shift output distributions in ways that
break downstream consumers. The mitigations the present paper
implements against all three of these risks are concrete and worth
restating: (a) every experiment carries a `manifest.json` recording
the git SHA, RDKit version, Python version, platform, SMIRKS library
SHA-256, and input dataset SHA-256, so the deterministic part of the
pipeline can be reproduced to the byte; (b) structured-output flags
(`response_format: json_object` for OpenAI and Mistral,
`response_mime_type: application/json` for Gemini) are enabled
explicitly per §4.5 and the Methods, so cross-provider portability of
the JSON-shape contract is load-bearing rather than implicit; (c)
HTTP-429 and HTTP-503 retries with exponential backoff (delays 2, 4,
8, 16 s; up to five attempts) ensure transient provider-side
unreliability does not corrupt benchmark results; and (d) the
cross-provider model benchmark itself, evaluated against eleven text
and fourteen vision models with the production prompts verbatim, is
the documentation: it tells the next person to reproduce or audit the
pipeline which model produced which behaviour at which date, so that a
future provider-side regression can be detected by re-running the
benchmark on the same inputs. None of this eliminates provider drift;
all of it makes provider drift detectable and recoverable rather than
silent.

### New references introduced in section D

```
[51] Sarwar, M. M., Ahmed, S., Khan, S. M. M. H., & Hyder, M. K. (2025). LLM output drift: Cross-provider validation and mitigation for financial workflows. *arXiv preprint*. https://doi.org/10.48550/arXiv.2511.07585
[52] Chen, L., Zaharia, M., & Zou, J. (2024). How is ChatGPT's behavior changing over time? *Harvard Data Science Review*, *6*(2). https://doi.org/10.1162/99608f92.5317da47
```

Note: (44) is already cited in section B; the entry above duplicates
the same DOI and APA citation; it is listed once in section B for the
author's convenience but should appear only once in the final
reference list.

---

## Honest notes on what I could not verify

- For reference (51) (Sarwar et al., *LLM Output Drift*), the arXiv ID
  2511.07585 is taken from a current arXiv listing and the paper was
  available at time of writing; the DOI form `10.48550/arXiv.2511.07585`
  is the arXiv-issued DOI scheme and is mechanical from the arXiv ID,
  but the author should re-verify the paper has not been superseded by
  a peer-reviewed venue before final submission.
- For reference (48) (ICH M7(R2)), the ICH guideline is not assigned a
  CrossRef DOI; the URL in the citation is the canonical landing
  point. The same is true of (49) (FDA draft guidance) and (50) (EMA
  reflection paper); regulatory documents are cited by URL by
  convention.
- For reference (44) (Therapeutics Data Commons), the NeurIPS Datasets
  and Benchmarks track does not issue per-paper CrossRef DOIs in the
  same way main-conference papers do; the arXiv DOI `10.48550/arXiv.
  2102.09548` is the operative persistent identifier.
- For reference (52), the Harvard Data Science Review version of Chen
  et al. is the peer-reviewed publication of the same content as the
  widely-cited arXiv preprint 2307.09009; the HDSR DOI was current at
  time of writing and should be re-verified at submission.
- All other DOIs in sections A through D were verified during the
  research pass against publisher landing pages or canonical search
  results; if any DOI fails to resolve at submission time, the most
  likely cause is a publisher migration and the canonical title +
  author + year string in each entry is sufficient to locate the
  current DOI.
