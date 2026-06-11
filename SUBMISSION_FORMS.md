# Preprint submission, form field text

Copy-paste the values below into the ChemRxiv and bioRxiv submission UIs. You should not need to edit anything; everything has been verified against the manuscript.

---

# ChemRxiv

URL: https://chemrxiv.org/engage/chemrxiv/dashboard
Click **Submit a Preprint** → **New Submission**.

## Field 1, Title

```
A vision-language agentic pipeline for lead optimization with chemistry-validity defence-in-depth
```

## Field 2, Content Type

Choose **Working Paper** (this matches the sample you shared and gives you the longest editorial flexibility for revisions).

## Field 3, Subject Classification (pick all that apply)

- **Chemistry > Cheminformatics**
- **Chemistry > Medicinal Chemistry**
- **Chemistry > Computational and Theoretical Chemistry**

(ChemRxiv allows up to three primary subjects. If forced to pick one, **Cheminformatics** is the canonical home for this work.)

## Field 4, Keywords

```
lead optimization, computer-aided drug design, matched molecular pairs, SMIRKS, vision-language models, pharmacophore preservation, ADMET, synthetic accessibility, SYBA, Bemis-Murcko scaffold, open-source cheminformatics, agentic pipelines, defence-in-depth
```

## Field 5, Abstract (paste in full)

```
Background: Lead optimization in small-molecule drug discovery is a constrained search problem: from a chemical starting point and the structural cues of its binding pose, propose analogs that preserve the pharmacophore, satisfy ADMET liabilities, and remain synthetically accessible. Individual components, pharmacophore alignment, SMIRKS transformation libraries, ADMET predictors, scaffold analysis, structural-alert filters, are mature, but the orchestration of these tools into a reproducible workflow that takes a lead and its ligand-interaction diagram (LID) as input and returns a ranked, filtered analog set is non-trivial.

Methods: We describe a twelve-stage agentic pipeline that combines a vision-language classifier of LIDs with a per-instance SMARTS construction step, deterministic structural gates, a curated 479-entry SMIRKS transformation library, an upstream ADMET-prediction backbone, and a synthetic-accessibility-anchored ranking. The architectural contribution is defence-in-depth: each agent stage is wrapped by a deterministic gate (chemistry-validity allowlists, soft Murcko ring-topology check, PAINS / Brenk structural-alert filters, ADMET-screen thresholds) so that perception errors cannot corrupt the downstream analog set.

Results: Across five evaluations, (i) a curated single-edit bioisosteric matched-molecular-pair pilot on which the library exact-recovers 16/30 = 53.3% of documented improving transformations; (ii) an unbiased ChEMBL-37-derived MMP scale-up of 2,000 pairs on which it exact-recovers 15.5% with mean best Tanimoto-to-target 0.755 in misses; (iii) a 129-marketed-drug scaffold-preservation and structural-alert audit showing the soft Murcko gate cuts the analog set roughly in half while raising scaffold preservation to 100%; (iv) a vision-language classifier self-consistency study on a fixed LID (pairwise Jaccard 1.00 across all 28 pair-comparisons, zero chemistry-validator drops); and (v) an end-to-end case study on two contrasting leads (DYRK1A kinase inhibitor and Linezolid antibacterial), in which a LID-aware run improves the rank-1 analog on both Pareto-style score (0.586 -> 0.638) and synthetic accessibility (2.51 -> 2.32), the defence-in-depth design preserves end-to-end output quality despite intermediate-stage variability. We additionally benchmark eleven language models across the three agent stages and report which configurations achieve reliable strict-JSON adherence and self-consistency, providing measured rather than asserted recommendations for the production default.

Conclusions: The pipeline demonstrates that a small set of deterministic structural gates around language-model agent stages is sufficient to absorb vision-classifier errors and produce constrained, pharmacophore-preserving lead optimization output on multiple target classes. The platform is implemented as production software; the code, data, manifest-stamped raw outputs, and reproduction scripts are released open source under the MIT licence at https://github.com/Nimieeee/lead-optimizer-paper.
```

## Field 6, Authors

| Field | Value |
|---|---|
| First name | Toluwanimi |
| Last name | Odunewu |
| Email | odunewutolu2@gmail.com |
| ORCID | 0009-0000-7053-9325 |
| Affiliation | Aisynth Labs (independent research) |
| Corresponding author | ✓ Yes |

## Field 7, Manuscript file

Upload the rendered PDF of `manuscript.md`. Since the manuscript source is in Markdown, render to PDF first:

```
# from the repo root
cd /Users/mac/Desktop/lead-optimizer-paper
pandoc manuscript.md -o manuscript.pdf --pdf-engine=xelatex
```

If you don't have pandoc + a LaTeX engine installed, an alternative is to open `manuscript.md` in VS Code with Markdown PDF extension or use https://md-to-pdf.fly.dev/ for a quick render.

The rendered PDF should be ~30–40 pages including figures.

## Field 8, Figures (upload separately, as ChemRxiv requests)

Upload all six PDFs from `figures/out/`:

```
fig1b_lead_optimizer_pipeline_snake.pdf
fig2_mmp_recovery.pdf
fig3_scaffold_alerts.pdf
fig4_vision_consistency.pdf
fig5_case_study.pdf
fig6_model_benchmark.pdf
```

## Field 9, Funding statement

```
This work received no external funding.
```

## Field 10, Conflict of interest statement

```
The author declares no competing financial interests.
```

## Field 11, Data and Code Availability statement

```
All code, raw experiment outputs, manifests, and reproduction scripts are released under the MIT licence at https://github.com/Nimieeee/lead-optimizer-paper. A frozen archive of the exact commit used to produce every figure and table in this manuscript is deposited on Zenodo at https://doi.org/10.5281/zenodo.20643485. The unbiased ChEMBL-37 matched-molecular-pair set was built from ChEMBL release 37 chemreps (https://ftp.ebi.ac.uk/pub/databases/chembl/) with the filter and mmpdb build pipeline included in the repository.
```

## Field 12, Ethics / human subjects

Select **No**: this work involves no human subjects, animal experiments, or clinical data.

## Field 13, License

Choose **CC BY 4.0** (the standard ChemRxiv default; allows reuse with attribution).

## Field 14, Cover letter / "Why this paper" box (optional)

```
This preprint introduces a vision-language agentic pipeline for lead optimization that integrates a vision classifier of ligand-interaction diagrams with deterministic chemistry-validity gates, a 479-entry SMIRKS library, ADMET prediction, and SYBA-anchored ranking. The contribution is the orchestration: each agent stage is wrapped by a deterministic gate so perception errors cannot corrupt the analog set. The pipeline is evaluated on five experiments including a 2,000-pair ChEMBL-derived MMP recovery benchmark and a cross-provider model evaluation across eleven language models. The platform is implemented as production software with code, data, and manifest-stamped outputs released open source.
```

---

# bioRxiv

URL: https://www.biorxiv.org/submit-a-manuscript
Click **Submit a manuscript** → **New Submission**.

## Field 1, Title

```
A vision-language agentic pipeline for lead optimization with chemistry-validity defence-in-depth
```

## Field 2, Article Type

Choose **New Results** (research with novel data, same flavour as ChemRxiv's "Working Paper").

## Field 3, Subject Area

Primary: **Bioinformatics** (closest fit; bioRxiv has no Cheminformatics subject)
Optional secondary: **Pharmacology and Toxicology**

## Field 4, Keywords (bioRxiv uses 3–10; pick the most relevant)

```
lead optimization
matched molecular pairs
vision-language models
ADMET prediction
synthetic accessibility
agentic pipelines
defence-in-depth
SMIRKS
```

## Field 5, Abstract

bioRxiv abstracts have a **~3000-character limit** (≈ 350 words). The ChemRxiv version above is 400+ words. Use this shorter version:

```
Lead optimization in small-molecule drug discovery is a constrained search problem: from a chemical starting point and the structural cues of its binding pose, propose analogs that preserve the pharmacophore, satisfy ADMET liabilities, and remain synthetically accessible. We describe a twelve-stage agentic pipeline that combines a vision-language classifier of ligand-interaction diagrams (LIDs) with a per-instance SMARTS construction step, deterministic structural gates, a curated 479-entry SMIRKS transformation library, an upstream ADMET-prediction backbone, and a synthetic-accessibility-anchored ranking. The architectural contribution is defence-in-depth: each agent stage is wrapped by a deterministic gate so perception errors cannot corrupt the downstream analog set.

We evaluate the pipeline on five experiments: a curated single-edit bioisosteric matched-molecular-pair pilot (exact recovery 53.3%, n=30); an unbiased ChEMBL-37-derived MMP scale-up (exact recovery 15.5%, n=2,000, mean best Tanimoto-to-target 0.755 in misses); a 129-marketed-drug scaffold-preservation and structural-alert audit showing the soft Murcko gate cuts the analog set roughly in half while raising scaffold preservation to 100%; a vision-language classifier self-consistency study on a fixed LID (pairwise Jaccard 1.00, zero chemistry-validator drops); and an end-to-end case study on DYRK1A and Linezolid in which a LID-aware run improves the rank-1 analog on both Pareto-style score (0.586 -> 0.638) and synthetic accessibility (2.51 -> 2.32). We additionally benchmark eleven language models across the three agent stages and report which configurations achieve reliable strict-JSON adherence.

The pipeline demonstrates that a small set of deterministic structural gates around language-model agent stages is sufficient to absorb vision-classifier errors and produce constrained, pharmacophore-preserving lead optimization output. The platform is implemented as production software; the code, data, manifest-stamped raw outputs, and reproduction scripts are released open source under the MIT licence at https://github.com/Nimieeee/lead-optimizer-paper.
```

## Field 6, Authors

Same as ChemRxiv above.

## Field 7, Manuscript file

Same PDF as for ChemRxiv.

## Field 8, Funding

```
This work received no external funding.
```

## Field 9, Conflict of interest

```
The author declares no competing financial interests.
```

## Field 10, Data and Code Availability

```
All code, raw experiment outputs, manifests, and reproduction scripts are released under the MIT licence at https://github.com/Nimieeee/lead-optimizer-paper. A frozen archive of the exact commit used to produce every figure and table in this manuscript is deposited on Zenodo at https://doi.org/10.5281/zenodo.20643485.
```

## Field 11, Ethics / human subjects

Select **No** for both human-subjects and animal-research questions.

## Field 12, License

bioRxiv lets you choose between **CC BY 4.0**, **CC BY-NC 4.0**, **CC BY-NC-ND 4.0**, or **No license (all rights reserved)**.

**Recommended: CC BY 4.0** (matches the ChemRxiv choice, maximises reuse).

## Field 13, Pre-existing preprint

If you submit to ChemRxiv **first** and bioRxiv **second**, bioRxiv asks if the paper has been posted elsewhere. Answer **Yes** and paste the ChemRxiv DOI (you'll get this after the ChemRxiv submission is accepted).

---

# Order I recommend

1. **Submit to ChemRxiv first** (more on-topic; more likely to surface to the right readers)
2. Wait for ChemRxiv acceptance (24–72 h moderation for first-time authors)
3. Once you have the ChemRxiv DOI, **cross-post to bioRxiv** (paste that DOI in the "previously posted" field)

This sequence is cleaner than the reverse because the ChemRxiv DOI then anchors the bioRxiv version as a clearly-marked cross-post.

# After acceptance, final mile

1. Drop the ChemRxiv DOI into manuscript front matter (replacing the current "ChemRxiv DOI, assigned at posting" placeholder)
2. Same for bioRxiv DOI
3. Push one final commit so the GitHub repo + Zenodo deposit reference the live ChemRxiv URL
4. The Zenodo deposit already exists and doesn't need to be re-minted, the existing DOI is the canonical archive DOI

That's it. You're done.
