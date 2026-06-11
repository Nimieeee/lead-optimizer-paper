# Reference Audit, *A vision-language agentic pipeline for lead optimization with chemistry-validity defence-in-depth*

Audit date: 2026-06-11
Auditor: independent citation review
Source manuscript: `paper/manuscript.md`

This audit is in three parts: (1) verification of the 12 numbered references, (2) factual / technical claims that need new citations, and (3) plagiarism flags.

---

## 1. Reference verification

Every cited DOI resolves and points to the claimed paper. Authors, year, volume, and page numbers are **correct** for all 12 references, with **two formatting nits** noted below.

| # | Status | Notes |
|---|---|---|
| 1, SYBA (Voršilák et al. 2020) | ✓ verified | DOI resolves. *J. Cheminform.* **2020**, *12*, 35. Authors and order match. |
| 2, ADMET-AI (Swanson et al. 2024) | ✓ verified | DOI resolves. *Bioinformatics* **2024**, *40* (7), btae416. Authors and order match. Manuscript reference omits issue number, see nit below. |
| 3, RDKit (Landrum et al.) | ⚠ formatting | Software is unversioned in the bibliography. Methods §6 lists RDKit 2026.03.3, the version-specific Zenodo DOI should be cited. See recommended fix below. |
| 4, Bemis–Murcko 1996 | ✓ verified | *J. Med. Chem.* **1996**, *39* (15), 2887–2893. Manuscript omits issue (15), minor, ACS allows either form. |
| 5, Chemprop / Yang 2019 | ✓ verified | *J. Chem. Inf. Model.* **2019**, *59* (8), 3370–3388. Authors and order match. |
| 6, PAINS (Baell 2010) | ✓ verified | *J. Med. Chem.* **2010**, *53* (7), 2719–2740. Authors match. |
| 7, Brenk 2008 | ✓ verified | *ChemMedChem* **2008**, *3* (3), 435–444. Authors match: Brenk, R.; Schipani, A.; James, D.; Krasowski, A.; Gilbert, I. H.; Frearson, J.; Wyatt, P. G. |
| 8, Ertl SAScore 2009 | ✓ verified | *J. Cheminform.* **2009**, *1*, 8. Authors match. |
| 9, mmpdb (Dalke 2018) | ✓ verified | *J. Chem. Inf. Model.* **2018**, *58* (5), 902–910. Authors match: Dalke, A.; Hert, J.; Kramer, C. |
| 10, REINVENT (Olivecrona 2017) | ✓ verified | *J. Cheminform.* **2017**, *9*, 48. Authors match. |
| 11, MOSES (Polykovskiy 2020) | ✓ verified | *Front. Pharmacol.* **2020**, *11*, 565644. All 16 authors match. |
| 12, GuacaMol (Brown 2019) | ✓ verified | *J. Chem. Inf. Model.* **2019**, *59* (3), 1096–1108. Authors match: Brown, N.; Fiscato, M.; Segler, M. H. S.; Vaucher, A. C. |

### Recommended formatting fixes

**Reference 2 (ADMET-AI)**, add issue number for full ACS style. Current: `*Bioinformatics* **2024**, *40*, btae416`. Recommended:

> Swanson, K.; Walther, P.; Leitz, J.; Mukherjee, S.; Wu, J. C.; Shivnaraine, R. V.; Zou, J. ADMET-AI: a machine learning ADMET platform for evaluation of large-scale chemical libraries. *Bioinformatics* **2024**, *40* (7), btae416. https://doi.org/10.1093/bioinformatics/btae416.

**Reference 3 (RDKit)**, the RDKit project explicitly asks authors to cite the version-specific Zenodo DOI. Methods §6 names RDKit 2026.03.3. Recommended:

> Landrum, G.; et al. RDKit: Open-source cheminformatics. Release 2026.03.3 (Q1 2026), 2026. https://doi.org/10.5281/zenodo.20446949 (accessed 2026-06).

(The concept-DOI fallback https://doi.org/10.5281/zenodo.591637 is acceptable if version pinning is undesirable, but version-pinning is the cheminformatics-community convention and is what reviewers will expect from a methods paper.)

**Reference 4 (Bemis–Murcko)**, strictly optional, but adding the issue number is the ACS-style standard: `*J. Med. Chem.* **1996**, *39* (15), 2887−2893.`

---

## 2. Missing citations

The manuscript names a number of standard cheminformatics methods, named filters, software, and domain concepts without citing them. Each is listed below with section, quoted phrase, proposed citation, and why that citation is the right one.

### A. Named metrics / filters / chemical-informatics methods

#### A1. Lipinski Rule of Five

- **Location:** §2.6 "applies hard structural validity (RDKit sanitisation, valency check), Lipinski Rule-of-Five, the PAINS catalogs…"; also Tables in §4.2 ("Lipinski-Ro5 pass") and §4.4 ("Lipinski 4.0"); also §6 ranking weights.
- **Proposed citation:**
  > Lipinski, C. A.; Lombardo, F.; Dominy, B. W.; Feeney, P. J. Experimental and computational approaches to estimate solubility and permeability in drug discovery and development settings. *Adv. Drug Delivery Rev.* **1997**, *23* (1–3), 3–25. https://doi.org/10.1016/S0169-409X(96)00423-1.
- **Why:** Lipinski et al. 1997 is the canonical Ro5 paper; every drug-discovery paper that uses Ro5 cites it. The 2001 reprint (*Adv. Drug Deliv. Rev.* **2001**, *46*, 3–26, DOI: 10.1016/S0169-409X(00)00129-0) is sometimes substituted but the 1997 original is correct.

#### A2. Tanimoto similarity (Morgan / ECFP4 fingerprints)

- **Location:** §3.1 "rank products by Tanimoto similarity (Morgan/ECFP4, radius 2, 2048 bits)"; §4.1 "every recovered analog at rank 1 by Tanimoto".
- **Proposed citations (both, because ECFP and Tanimoto have distinct origins):**
  > Rogers, D.; Hahn, M. Extended-connectivity fingerprints. *J. Chem. Inf. Model.* **2010**, *50* (5), 742–754. https://doi.org/10.1021/ci100050t.

  > Bajusz, D.; Rácz, A.; Héberger, K. Why is Tanimoto index an appropriate choice for fingerprint-based similarity calculations? *J. Cheminform.* **2015**, *7*, 20. https://doi.org/10.1186/s13321-015-0069-3.
- **Why:** Rogers & Hahn 2010 is the canonical ECFP paper. The Tanimoto coefficient itself dates to Tanimoto's 1958 IBM technical report and Jaccard 1901, but for the cheminformatics-specific justification of Tanimoto-on-binary-fingerprints, Bajusz et al. 2015 is the modern standard reference. If the author wants a single citation, Rogers & Hahn alone is acceptable since it defines both the fingerprint and the similarity metric in context.

#### A3. QED (quantitative estimate of drug-likeness)

- **Location:** §4.4 "QED 0.88", "QED 0.82" in the DYRK1A rank-1 / rank-3 analog descriptions.
- **Proposed citation:**
  > Bickerton, G. R.; Paolini, G. V.; Besnard, J.; Muresan, S.; Hopkins, A. L. Quantifying the chemical beauty of drugs. *Nat. Chem.* **2012**, *4* (2), 90–98. https://doi.org/10.1038/nchem.1243.
- **Why:** Sole canonical QED reference. RDKit's `QED.qed` implementation is a direct port of Bickerton et al. 2012.

#### A4. Bemis–Murcko scaffold, beyond the existing citation

- **Location:** Reference 4 already covers the *concept* of the Murcko scaffold. The current Bemis–Murcko citation is fine; no action needed. (Noting it here only so the reader is not surprised that no second citation is recommended.)

#### A5. Matched molecular pairs (MMP), concept

- **Location:** §1 introduces "transformation libraries (SMIRKS)" and §3.1 builds an MMP set; §3 / §4.1 use the MMP framing throughout.
- **Proposed citation:**
  > Griffen, E.; Leach, A. G.; Robb, G. R.; Warner, D. J. Matched molecular pairs as a medicinal chemistry tool. *J. Med. Chem.* **2011**, *54* (22), 7739–7750. https://doi.org/10.1021/jm200452d.

  (Optional companion, since the concept predates Griffen 2011:)
  > Kenny, P. W.; Sadowski, J. Structure modification in chemical databases. In *Chemoinformatics in Drug Discovery*; Oprea, T. I., Ed.; Wiley-VCH: Weinheim, 2005; pp 271–285.
- **Why:** Griffen et al. 2011 is the most-cited review establishing MMP as a medicinal-chemistry methodology. The Kenny & Sadowski 2005 chapter is the algorithmic origin and is sometimes cited alongside. mmpdb (ref 9) is software, not the MMP concept, these are separate things and citing only mmpdb misrepresents the methodology's origin.

#### A6. Pharmacophore (as a defined concept)

- **Location:** §1 ("pharmacophore alignment"), §2.6 (`enforce_pharmacophore`), abstract ("preserve the pharmacophore"). Used throughout but never defined or cited.
- **Proposed citation:**
  > Wermuth, C. G.; Ganellin, C. R.; Lindberg, P.; Mitscher, L. A. Glossary of terms used in medicinal chemistry (IUPAC Recommendations 1998). *Pure Appl. Chem.* **1998**, *70* (5), 1129–1143. https://doi.org/10.1351/pac199870051129.
- **Why:** The IUPAC 1998 glossary is the canonical definitional reference for "pharmacophore". If the author prefers a methods reference instead, Wolber & Langer 2005 (Wolber, G.; Langer, T. LigandScout: 3-D pharmacophores derived from protein-bound ligands and their use as virtual screening filters. *J. Chem. Inf. Model.* **2005**, *45* (1), 160–169. https://doi.org/10.1021/ci049885e) is the most common alternative.

#### A7. Bioisosteres

- **Location:** §3.1 "30 single-edit literature-documented bioisosteric matched pairs"; §4.1 "the library proposes valid alternative bioisosteres".
- **Proposed citation:**
  > Meanwell, N. A. Synopsis of some recent tactical application of bioisosteres in drug design. *J. Med. Chem.* **2011**, *54* (8), 2529–2591. https://doi.org/10.1021/jm1013693.
- **Why:** Meanwell 2011 is the most-cited modern review of bioisosterism in medicinal chemistry. Patani & LaVoie 1996 (*Chem. Rev.* **1996**, *96* (8), 3147–3176, DOI: 10.1021/cr950066q) is an older alternative; either is defensible.

#### A8. SMARTS / SMIRKS specification

- **Location:** Throughout, §2.4 SMARTS construction, §3.1 SMIRKS library, §6 SMIRKS library inventory.
- **Proposed citation:** Daylight SMARTS / SMIRKS specifications are not journal-published; the canonical citation form is:
  > Daylight Chemical Information Systems, Inc. *Daylight Theory Manual, SMARTS: A Language for Describing Molecular Patterns*. https://www.daylight.com/dayhtml/doc/theory/theory.smarts.html (accessed 2026-06).

  > Daylight Chemical Information Systems, Inc. *Daylight Theory Manual, SMIRKS: A Reaction Transform Language*. https://www.daylight.com/dayhtml/doc/theory/theory.smirks.html (accessed 2026-06).
- **Why:** SMARTS and SMIRKS are Daylight proprietary specifications. There is no peer-reviewed journal paper. The Daylight Theory Manual URLs are the universally-accepted citation form across cheminformatics.

#### A9. SMILES specification (used implicitly throughout)

- **Location:** §2.1 "lead SMILES (required)", §3.1 canonical-SMILES, §6, etc.
- **Proposed citation:**
  > Weininger, D. SMILES, a chemical language and information system. 1. Introduction to methodology and encoding rules. *J. Chem. Inf. Comput. Sci.* **1988**, *28* (1), 31–36. https://doi.org/10.1021/ci00057a005.
- **Why:** Weininger 1988 is the SMILES origin paper. Standard practice is to cite once at first SMILES mention.

### B. Named ML / generative-model background

#### B1. Chemprop V2 (versus V1)

- **Location:** §2.5 "the upstream `admet_ai` Chemprop-v2 Graph Neural Network⁵"; §6 "`admet_ai` 1.x (Chemprop-v2 ADMET)".
- **Issue:** Reference 5 (Yang et al. 2019) is the **original Chemprop (V1)** paper. Chemprop V2 has a separate publication that should be cited when V2 is named explicitly:
  > Heid, E.; Greenman, K. P.; Chung, Y.; Li, S.-C.; Graff, D. E.; Vermeire, F. H.; Wu, H.; Green, W. H.; McGill, C. J. Chemprop: A machine learning package for chemical property prediction. *J. Chem. Inf. Model.* **2024**, *64* (1), 9–17. https://doi.org/10.1021/acs.jcim.3c01250.
- **Why:** Heid et al. 2024 is the explicit Chemprop V2 paper. Citing only Yang 2019 when the manuscript names V2 is a small but real provenance gap that reviewers will catch.

#### B2. Graph Neural Networks (general framing)

- **Location:** §2.5 "Chemprop-v2 Graph Neural Network".
- **Recommendation:** No new citation strictly required, Yang 2019 / Heid 2024 cover the GNN itself in the molecular-property-prediction context. Optional supplementary: Gilmer et al. 2017 (MPNN), but most reviewers will not require this.

### C. Named databases

#### C1. ChEMBL-37

- **Location:** Abstract ("ChEMBL-37–derived MMP scale-up"); §3.1 ("2000-compound drug-like subset of ChEMBL-37"); §4.1 (Figure 2 caption).
- **Proposed citations (both, version-specific release notice + canonical):**
  > Zdrazil, B.; Felix, E.; Hunter, F.; Manners, E. J.; Blackshaw, J.; Corbett, S.; de Veij, M.; Ioannidis, H.; Lopez, D. M.; Mosquera, J. F.; Magariños, M. P.; Bosc, N.; Arcila, R.; Kizilören, T.; Gaulton, A.; Bento, A. P.; Adasme, M. F.; Monecke, P.; Landrum, G. A.; Leach, A. R. The ChEMBL Database in 2023: a drug discovery platform spanning multiple bioactivity data types and time periods. *Nucleic Acids Res.* **2024**, *52* (D1), D1180–D1192. https://doi.org/10.1093/nar/gkad1004.
- **Why:** Zdrazil et al. 2024 is the most recent peer-reviewed ChEMBL database paper and is the standard reference today. ChEMBL-37 itself does not have a separate paper, the EBI release notes are not citable independently. Some authors additionally cite Gaulton et al. 2017 (DOI: 10.1093/nar/gkw1074) for the database history but the 2024 paper is the current standard.

### D. Domain claims that need provenance

#### D1. DYRK1A as a kinase / CNS-relevant target

- **Location:** §3.3 "the DYRK1A Compound 25014 binding pose"; §3.4 "(a) Compound 25014, a methoxy- and benzyl-alcohol-substituted benzodioxin from a kinase/CNS series"; §4.4 LID-aware case study.
- **Proposed citation:**
  > Becker, W.; Sippl, W. Activation, regulation, and inhibition of DYRK1A. *FEBS J.* **2011**, *278* (2), 246–256. https://doi.org/10.1111/j.1742-4658.2010.07956.x.
- **Why:** Becker & Sippl 2011 is the most-cited review of DYRK1A as a drug target including its CNS relevance (Alzheimer's, Down syndrome). One review-style citation here is enough to establish the target as a recognised CNS-kinase indication and to justify the BBB prioritisation in §2.5.

#### D2. Linezolid as oxazolidinone antibacterial

- **Location:** Abstract ("Linezolid antibacterial"); §3.4 ("an FDA-approved oxazolidinone gram-positive antibacterial"); §4.4.
- **Proposed citation:**
  > Brickner, S. J.; Hutchinson, D. K.; Barbachyn, M. R.; Manninen, P. R.; Ulanowicz, D. A.; Garmon, S. A.; Grega, K. C.; Hendges, S. K.; Toops, D. S.; Ford, C. W.; Zurenko, G. E. Synthesis and antibacterial activity of U-100592 and U-100766, two oxazolidinone antibacterial agents for the potential treatment of multidrug-resistant Gram-positive bacterial infections. *J. Med. Chem.* **1996**, *39* (3), 673–679. https://doi.org/10.1021/jm9509556.
- **Why:** This is the original Pharmacia & Upjohn discovery paper for Linezolid (U-100766) and Eperezolid (U-100592). It establishes linezolid as an oxazolidinone and as a gram-positive antibacterial, both claims the manuscript makes. A lighter alternative is the Linezolid FDA label or the more recent Foti et al. 2021 review, but Brickner 1996 is the citation reviewers expect for the chemotype claim.

#### D3. Chemprop V2's role in ADMET-AI

- **Location:** §2.5 "single forward pass through the upstream `admet_ai` Chemprop-v2 Graph Neural Network⁵ on the lead molecule yields the 54-endpoint baseline".
- **Issue:** The connection (ADMET-AI uses Chemprop V2 internally) is itself a citable claim, it is documented in the ADMET-AI paper (ref 2). No new citation needed; this is just an editorial note that ref 2 already substantiates this claim.

### E. Load-bearing software not cited

The author already names several software packages without citation. Standard ACS practice cites software that is *methodologically load-bearing* and treats peripheral tooling as optional.

#### E1. WeasyPrint (PDF generation)

- **Location:** §2.8 "the top-K analogs are written to PDF (via WeasyPrint)"; §6.
- **Recommendation:** **Optional.** WeasyPrint is reporting infrastructure, not methodology. A footnote URL (`https://weasyprint.org`) suffices. No citation required if the author prefers a clean reference list.

#### E2. FastAPI / Supabase

- **Location:** §6 "FastAPI (HTTP layer) and Supabase (storage) are used by the production deploy but are not load-bearing for the methodology".
- **Recommendation:** The author has already disclaimed these as non-load-bearing. **No citation needed.**

#### E3. PLIP (mentioned as future work)

- **Location:** §5.2 "A follow-on benchmark using a PLIP-derived silver-standard interaction set".
- **Proposed citation:**
  > Salentin, S.; Schreiber, S.; Haupt, V. J.; Adasme, M. F.; Schroeder, M. PLIP: fully automated protein–ligand interaction profiler. *Nucleic Acids Res.* **2015**, *43* (W1), W443–W447. https://doi.org/10.1093/nar/gkv315.
- **Why:** PLIP is named as a tool the author intends to use for gold-standard generation. Standard practice is to cite a tool at first mention even if usage is forthcoming.

#### E4. Murcko scaffold implementation in RDKit

- No citation needed, ref 3 (RDKit) and ref 4 (Bemis–Murcko) already cover this between them.

### F. Stage 2 / Stage 5 / Stage 6 vision-language and structured-output claims

#### F1. Structured-output API claim

- **Location:** §4.5 / §6: "`response_format: json_object` for OpenAI/Mistral, `response_mime_type: application/json` for Gemini".
- **Recommendation:** These are provider-specific API features documented in vendor documentation, not peer-reviewed publications. Standard practice is to cite the vendor docs as URLs accessed on a given date if the claim is load-bearing. The manuscript's claim is moderately load-bearing for the §4.5 cross-provider conclusion, so a footnote URL is appropriate but a formal reference is not required.

#### F2. JSON / strict-JSON output framing

- No citation needed, this is engineering practice, not a method.

### G. Statistical / experimental terms

#### G1. "Pareto front" / Pareto-style ranking

- **Location:** §2.8 "We label the rank a 'Pareto-style penalty rank'…"; §5.2 "A real Pareto-front implementation…"; abstract.
- **Recommendation:** "Pareto front" is general optimization terminology; the manuscript already disclaims the implementation does not produce one. **No citation strictly needed**, though the author may want to cite a multi-objective optimization reference (e.g. Deb 2001) if they intend to implement a true Pareto front in future work. Not required for this paper.

#### G2. Jaccard similarity

- **Location:** §3.3 "pairwise Jaccard similarity"; §4.3.
- **Recommendation:** **No citation required.** Jaccard is taught in undergraduate statistics; standard cheminformatics papers do not cite Jaccard 1901.

### H. Summary table of recommended new citations

| Section | Concept | Proposed citation (short) | Priority |
|---|---|---|---|
| §2.6, §4.2, §4.4 | Lipinski Rule of Five | Lipinski 1997 *Adv. Drug Deliv. Rev.* | **High** |
| §3.1, §4.1 | Morgan / ECFP4 fingerprints + Tanimoto | Rogers & Hahn 2010 *J. Chem. Inf. Model.* | **High** |
| §4.4 | QED | Bickerton 2012 *Nat. Chem.* | **High** |
| §3.1, §3, §4 | Matched molecular pairs (concept) | Griffen 2011 *J. Med. Chem.* | **High** |
| §1, §2.6 | Pharmacophore | Wermuth IUPAC 1998 *Pure Appl. Chem.* | Medium |
| §3.1, §4.1 | Bioisosteres | Meanwell 2011 *J. Med. Chem.* | Medium |
| §2.4, §3.1, §6 | SMARTS / SMIRKS spec | Daylight Theory Manual URLs | **High** |
| §2.1 etc. | SMILES spec | Weininger 1988 *J. Chem. Inf. Comput. Sci.* | Medium |
| §2.5, §6 | Chemprop V2 specifically | Heid 2024 *J. Chem. Inf. Model.* | **High** |
| Abstract, §3.1 | ChEMBL-37 database | Zdrazil 2024 *Nucleic Acids Res.* | **High** |
| §3.3, §3.4, §4.4 | DYRK1A as kinase / CNS target | Becker & Sippl 2011 *FEBS J.* | Medium |
| Abstract, §3.4 | Linezolid as oxazolidinone | Brickner 1996 *J. Med. Chem.* | Medium |
| §5.2 | PLIP | Salentin 2015 *Nucleic Acids Res.* | Low (forward-looking only) |

---

## 3. Plagiarism flags

Most of the manuscript is original prose. The following passages read close to canonical definitional phrasings used widely across the cheminformatics literature and are worth re-checking before submission. None of these are clear plagiarism, they are flagged because canonical definitions are the highest-risk place for accidental copying.

### 3.1 SYBA description (§2.7)

> "SYBA is a naive-Bayes classifier over ECFP4 fragments, AUC > 0.81 on the Sci-Finder reactivity dataset; the signed score is positive for synthesisable molecules and negative for hard-to-make molecules, with a magnitude roughly in [–50, +50]."

Compare to Voršilák et al. 2020 (ref 1), which describes SYBA as "a Bernoulli naïve Bayes classifier that assigns SYBA score contributions to individual fragments based on their frequencies in databases of easy and hard-to-synthesize molecules" and uses the "easy / hard-to-make" framing. The paraphrase is close but the manuscript adds the score-range and AUC numbers that don't appear in the same sentence in the original. **Verdict: borderline-safe paraphrase**, but consider tightening to "SYBA, a Bernoulli naïve-Bayes classifier (Voršilák 2020, ref 1)…" to make the attribution explicit.

### 3.2 PAINS description (implicit)

The manuscript does not explicitly define PAINS, so there is no direct definitional copying. PAINS is named in §2.6 and §4.2 and cited (ref 6), fine.

### 3.3 Bemis–Murcko description (§2.1, §2.4, §6)

The manuscript writes: "compute the Bemis–Murcko scaffold atom set and SMARTS" and (Methods) "The Bemis–Murcko scaffold SMARTS is appended to the restricted-SMARTS set".

This is functional description, not a definition. **No flag.**

### 3.4 Lipinski Ro5

The manuscript only names "Lipinski Rule-of-Five" and does not define it. **No flag**, but A1 above still applies: it needs a citation even if undefined.

### 3.5 Ertl SAScore framing (§2.7)

> "Ertl's SAScore⁸ is computed in parallel and retained as a legacy field for audit but is not surfaced."

This is procedural prose, not a definition. **No flag.**

### 3.6 "Pan-assay interference compounds (PAINS)"

The phrase "pan-assay interference compounds" is from Baell & Holloway 2010 (ref 6). It is technical terminology and not subject to plagiarism concern; the citation is already in place. **No flag.**

### 3.7 Chemprop / MPNN description

The manuscript only names "Chemprop-v2 Graph Neural Network", no definitional prose. **No flag.**

### 3.8 Glossary-style passages

§2.6 lists filters: "Lipinski Rule-of-Five, the PAINS catalogs (A, B, C), and the Brenk filter". These are named items, not definitions. **No flag**, but reviewers will want citations (covered in §2 above).

### 3.9 Caveat about self-consistency vs accuracy (§4.3)

> "Perfect pairwise Jaccard reflects the platform's vision-prompt running with deterministic settings… The number measures *reproducibility*, not *accuracy*: the model could be consistently wrong."

This phrasing is original and well-written. **No flag.** Mentioned only because reviewers sometimes flag "X measures reproducibility, not accuracy" as a common phrase, here it is used correctly and unambiguously.

### Plagiarism summary

**Net verdict: no outright plagiarism detected.** The §2.7 SYBA description is the one passage worth a second pass, the rest of the manuscript is original prose. The author's habit of explicitly distinguishing "the contribution is the orchestration, not any single component" (§5.1) is the right defensive framing and reads as genuinely original.

---

## Appendix A, Reference-list rewrite (recommended)

A clean, ACS-style reference list incorporating the fixes above and the 13 new recommended citations would look like this (numbering changes; original 1–12 preserved by content):

```
(1)  Voršilák, M.; Kolář, M.; Čmelo, I.; Svozil, D. SYBA: Bayesian estimation of synthetic
     accessibility of organic compounds. *J. Cheminform.* **2020**, *12*, 35.
     https://doi.org/10.1186/s13321-020-00439-2.

(2)  Swanson, K.; Walther, P.; Leitz, J.; Mukherjee, S.; Wu, J. C.; Shivnaraine, R. V.;
     Zou, J. ADMET-AI: a machine learning ADMET platform for evaluation of large-scale
     chemical libraries. *Bioinformatics* **2024**, *40* (7), btae416.
     https://doi.org/10.1093/bioinformatics/btae416.

(3)  Heid, E.; Greenman, K. P.; Chung, Y.; Li, S.-C.; Graff, D. E.; Vermeire, F. H.; Wu,
     H.; Green, W. H.; McGill, C. J. Chemprop: A machine learning package for chemical
     property prediction. *J. Chem. Inf. Model.* **2024**, *64* (1), 9–17.
     https://doi.org/10.1021/acs.jcim.3c01250.

(4)  Yang, K.; Swanson, K.; Jin, W.; Coley, C.; Eiden, P.; Gao, H.; Guzman-Perez, A.;
     Hopper, T.; Kelley, B.; Mathea, M.; Palmer, A.; Settels, V.; Jaakkola, T.; Jensen, K.;
     Barzilay, R. Analyzing learned molecular representations for property prediction. *J.
     Chem. Inf. Model.* **2019**, *59* (8), 3370–3388.
     https://doi.org/10.1021/acs.jcim.9b00237.

(5)  Landrum, G.; et al. RDKit: Open-source cheminformatics. Release 2026.03.3, 2026.
     https://doi.org/10.5281/zenodo.20446949 (accessed 2026-06).

(6)  Bemis, G. W.; Murcko, M. A. The properties of known drugs. 1. Molecular frameworks.
     *J. Med. Chem.* **1996**, *39* (15), 2887–2893. https://doi.org/10.1021/jm9602928.

(7)  Lipinski, C. A.; Lombardo, F.; Dominy, B. W.; Feeney, P. J. Experimental and
     computational approaches to estimate solubility and permeability in drug discovery
     and development settings. *Adv. Drug Delivery Rev.* **1997**, *23* (1–3), 3–25.
     https://doi.org/10.1016/S0169-409X(96)00423-1.

(8)  Bickerton, G. R.; Paolini, G. V.; Besnard, J.; Muresan, S.; Hopkins, A. L. Quantifying
     the chemical beauty of drugs. *Nat. Chem.* **2012**, *4* (2), 90–98.
     https://doi.org/10.1038/nchem.1243.

(9)  Rogers, D.; Hahn, M. Extended-connectivity fingerprints. *J. Chem. Inf. Model.*
     **2010**, *50* (5), 742–754. https://doi.org/10.1021/ci100050t.

(10) Baell, J. B.; Holloway, G. A. New substructure filters for removal of pan-assay
     interference compounds (PAINS) from screening libraries and for their exclusion in
     bioassays. *J. Med. Chem.* **2010**, *53* (7), 2719–2740.
     https://doi.org/10.1021/jm901137j.

(11) Brenk, R.; Schipani, A.; James, D.; Krasowski, A.; Gilbert, I. H.; Frearson, J.;
     Wyatt, P. G. Lessons learnt from assembling screening libraries for drug discovery for
     neglected diseases. *ChemMedChem* **2008**, *3* (3), 435–444.
     https://doi.org/10.1002/cmdc.200700139.

(12) Ertl, P.; Schuffenhauer, A. Estimation of synthetic accessibility score of drug-like
     molecules based on molecular complexity and fragment contributions. *J. Cheminform.*
     **2009**, *1*, 8. https://doi.org/10.1186/1758-2946-1-8.

(13) Daylight Chemical Information Systems, Inc. *Daylight Theory Manual, SMARTS: A
     Language for Describing Molecular Patterns*.
     https://www.daylight.com/dayhtml/doc/theory/theory.smarts.html (accessed 2026-06).

(14) Daylight Chemical Information Systems, Inc. *Daylight Theory Manual, SMIRKS: A
     Reaction Transform Language*.
     https://www.daylight.com/dayhtml/doc/theory/theory.smirks.html (accessed 2026-06).

(15) Weininger, D. SMILES, a chemical language and information system. 1. Introduction to
     methodology and encoding rules. *J. Chem. Inf. Comput. Sci.* **1988**, *28* (1),
     31–36. https://doi.org/10.1021/ci00057a005.

(16) Griffen, E.; Leach, A. G.; Robb, G. R.; Warner, D. J. Matched molecular pairs as a
     medicinal chemistry tool. *J. Med. Chem.* **2011**, *54* (22), 7739–7750.
     https://doi.org/10.1021/jm200452d.

(17) Meanwell, N. A. Synopsis of some recent tactical application of bioisosteres in drug
     design. *J. Med. Chem.* **2011**, *54* (8), 2529–2591.
     https://doi.org/10.1021/jm1013693.

(18) Wermuth, C. G.; Ganellin, C. R.; Lindberg, P.; Mitscher, L. A. Glossary of terms used
     in medicinal chemistry (IUPAC Recommendations 1998). *Pure Appl. Chem.* **1998**, *70*
     (5), 1129–1143. https://doi.org/10.1351/pac199870051129.

(19) Dalke, A.; Hert, J.; Kramer, C. mmpdb: An open-source matched molecular pair platform
     for large multiproperty data sets. *J. Chem. Inf. Model.* **2018**, *58* (5), 902–910.
     https://doi.org/10.1021/acs.jcim.8b00173.

(20) Olivecrona, M.; Blaschke, T.; Engkvist, O.; Chen, H. Molecular de-novo design through
     deep reinforcement learning. *J. Cheminform.* **2017**, *9*, 48.
     https://doi.org/10.1186/s13321-017-0235-x.

(21) Polykovskiy, D.; Zhebrak, A.; Sanchez-Lengeling, B.; Golovanov, S.; Tatanov, O.;
     Belyaev, S.; Kurbanov, R.; Artamonov, A.; Aladinskiy, V.; Veselov, M.; Kadurin, A.;
     Johansson, S.; Chen, H.; Nikolenko, S.; Aspuru-Guzik, A.; Zhavoronkov, A. Molecular
     Sets (MOSES): A benchmarking platform for molecular generation models. *Front.
     Pharmacol.* **2020**, *11*, 565644. https://doi.org/10.3389/fphar.2020.565644.

(22) Brown, N.; Fiscato, M.; Segler, M. H. S.; Vaucher, A. C. GuacaMol: Benchmarking models
     for de novo molecular design. *J. Chem. Inf. Model.* **2019**, *59* (3), 1096–1108.
     https://doi.org/10.1021/acs.jcim.8b00839.

(23) Zdrazil, B.; Felix, E.; Hunter, F.; et al. The ChEMBL Database in 2023: a drug
     discovery platform spanning multiple bioactivity data types and time periods.
     *Nucleic Acids Res.* **2024**, *52* (D1), D1180–D1192.
     https://doi.org/10.1093/nar/gkad1004.

(24) Becker, W.; Sippl, W. Activation, regulation, and inhibition of DYRK1A. *FEBS J.*
     **2011**, *278* (2), 246–256. https://doi.org/10.1111/j.1742-4658.2010.07956.x.

(25) Brickner, S. J.; Hutchinson, D. K.; Barbachyn, M. R.; Manninen, P. R.; Ulanowicz, D.
     A.; Garmon, S. A.; Grega, K. C.; Hendges, S. K.; Toops, D. S.; Ford, C. W.; Zurenko,
     G. E. Synthesis and antibacterial activity of U-100592 and U-100766, two oxazolidinone
     antibacterial agents for the potential treatment of multidrug-resistant Gram-positive
     bacterial infections. *J. Med. Chem.* **1996**, *39* (3), 673–679.
     https://doi.org/10.1021/jm9509556.

(26) Salentin, S.; Schreiber, S.; Haupt, V. J.; Adasme, M. F.; Schroeder, M. PLIP: fully
     automated protein–ligand interaction profiler. *Nucleic Acids Res.* **2015**, *43*
     (W1), W443–W447. https://doi.org/10.1093/nar/gkv315.
```

(Renumbering reflects approximate first-mention order. The author should keep whichever ordering convention they prefer.)

---

## Appendix B, One-line summary of audit findings

- **12 of 12** existing references resolve and are factually correct. Two formatting nits (issue numbers, RDKit version-specific DOI).
- **12 high-priority** new citations are recommended: Lipinski, Rogers & Hahn (ECFP), Bickerton (QED), Griffen (MMP concept), Daylight SMARTS, Daylight SMIRKS, Heid (Chemprop V2), Zdrazil (ChEMBL-37), Wermuth (pharmacophore IUPAC), Meanwell (bioisosteres), Weininger (SMILES), Becker & Sippl (DYRK1A), Brickner (Linezolid).
- **1 borderline plagiarism passage** worth a re-read: the §2.7 SYBA description. Otherwise prose is original.
