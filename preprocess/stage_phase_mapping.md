# Native Stage → Developmental Phase Mapping (DRAFT for review)

Universal phase vocabulary (CONTEXT.md): `blastula`, `gastrula`, `neurula`, `organogenesis`
(`fetal` reserved, currently unused). Invertebrates have no true neurula — the
phylotypic/morphogenesis period is mapped to `neurula` for cross-species alignment.

These mappings become per-dataset `stage_mapping` dicts in the run manifest.

## Vertebrates

| Dataset | Native stage(s) | Phase |
|---|---|---|
| Human CS6 Stereo-seq (fig1–3) | CS6 | gastrula |
| Human CS7 (Tyser sc + spatial) | CS7 | gastrula |
| Human CS8 spatial | CS8 | neurula |
| Human CS9 Stereo, CS10 | CS9, CS10 (`PCW3 / CS10`) | neurula |
| Human CS12–16 | CS12, CS13-14, CS15-16 | organogenesis |
| Mouse TOME | E3.5, E4.5, E5.25, E5.5 | blastula |
| | E6.25, E6.5, E6.75, E7.0, E7.25, E7.5, E7.75 | gastrula |
| | E8.0, E8.25, E8.5a, E8.5b | neurula |
| | E9.5, E10.5, E11.5, E12.5, E13.5 | organogenesis |
| Mouse gastrulation atlas | E6.5–E7.75, mixed_gastrulation | gastrula |
| | E8.0, E8.25, E8.5 | neurula |
| Mouse single-embryo timecourse | developmental_time < 8.0 | gastrula |
| | developmental_time ≥ 8.0 | neurula |
| Rabbit atlas | GD7 | gastrula |
| | GD8 | neurula |
| | GD9 | organogenesis |
| Zebrafish (Wagner 2018) | 4hpf | blastula |
| | 6hpf, 8hpf, 10hpf | gastrula |
| | 14hpf, 18hpf, 24hpf | neurula |
| Chicken (eLife 2022) | HH4 | gastrula |
| | HH5, HH6, HH7 | neurula |

## Invertebrates

| Dataset | Native stage(s) | Phase |
|---|---|---|
| Drosophila continuum | hrs_00_02, hrs_01_03 | blastula |
| | hrs_02_04, hrs_03_07 | gastrula |
| | hrs_04_08, hrs_06_10 (extended germ band) | neurula |
| | hrs_08_12, hrs_10_14, hrs_12_16, hrs_14_18, hrs_16_20 | organogenesis |
| C. elegans (embryo.time.bin, min) | < 100 | blastula |
| | 100-130, 130-170, 170-210, 210-270 | gastrula |
| | 270-330, 330-390 (comma/morphogenesis) | neurula |
| | 390-450, 450-510, 510-580, 580-650, > 650 | organogenesis |
| Sea urchin (hpf) | 2, 3, 4, 5, 6, 7, 8, 9 | blastula |
| | 10, 11, 12, 13, 14, 15, 16 | gastrula |
| | 18, 20, 24 (prism/early larva) | organogenesis |

## Boundary calls — resolved 2026-09-09

All boundary calls are now literature-anchored; see `docs/perturbation-and-baseline-design.md`
§5 for the full citation table (human CS8–CS10, mouse E8.0–8.5, rabbit GD9, zebrafish
14–18 hpf, fly germ-band, worm comma, urchin 10–16 hpf, chicken HH4–7).

- **Fly sliding windows (hrs_XX_YY)**: the Calderon atlas labels are overlapping 4 h sampling
  windows with 2 h offsets, not stages. Each window is assigned exactly one phase **by its
  midpoint** (germ-band extension ≈ 4–9 h → neurula; hrs_08_12 midpoint 10 → organogenesis).
  The current mapping is midpoint-consistent; overlapping windows are acceptable for training,
  but phase-resolved analyses must assign each cell one phase via window midpoint (or the
  atlas's per-cell estimated age if exported).
- **Zebrafish 14–24 hpf → neurula** is a phylotypic-alignment convention (Kimmel staging has
  no "neurula"; 14–18 hpf = segmentation, 24 hpf = pharyngula onset). Documented convention,
  not fact.
- **Sensitivity analysis (pre-registered):** shift every boundary one native-stage bin in each
  direction, re-run headline metrics; acceptance = top-100 perturbation hits per stratum
  retain ≥ 80% membership under both shifts.

## Recorded decisions (2026-09-09, user-approved)

- **C. elegans 100–130 min bin moved blastula → gastrula.** C. elegans gastrulation
  begins at the 26–28 cell stage (~100 min post-fertilization), so the 100–130 bin is
  predominantly gastrulating, not blastula. Decision: treat as gastrula (option 1);
  recorded here because it shifts phase composition for the worm dataset.
- **Zebrafish 24hpf moved organogenesis → neurula.** 24 hpf is the pharyngula period
  onset (phylotypic stage), which this mapping aligns to `neurula` for cross-species
  comparability. Decision: neurula (option 1); recorded here because it shifts the
  zebrafish phase composition.
## Probe species (zero-shot evaluation)

Same universal phase vocabulary and conventions as the training species above
(invertebrate phylotypic/morphogenesis period → `neurula` where no true neurula
exists). Native stage labels below are the exact values in each H5AD's `obs`.

### Vertebrates

| Dataset | Native stage(s) | Phase |
|---|---|---|
| Macaque CS8–CS11 sc (Zhai 2022) | CS8 (`E20`), CS9 (`E23`), CS11 (`E26`, `E29`) | neurula |
| Macaque ex utero (Gong 2023) | ME18, ME19, ME20 | gastrula |
| | ME21, ME22, ME23, ME24, ME25 | neurula |
| Macaque CS9–CS10 spatial atlas | CS9, CS10 | neurula |
| Pig gastrulation atlas (Simpson 2024) | E11.5, E12, E12.5, E13 | gastrula |
| | E13.5, E14, E14.5, E15 | neurula |
| Guinea pig preimplantation (Canizo 2025) | 8C, 16C, 16-32 cell, EB, MB, LB (`E3.5`–`E6`) | blastula |
| Xenopus (Briggs 2018) | Stage_8 | blastula |
| | Stage_10, Stage_11, Stage_12, Stage_13 | gastrula |
| | Stage_14, Stage_16, Stage_18, Stage_20 | neurula |
| | Stage_22 (early tailbud) | organogenesis |

### Invertebrates

| Dataset | Native stage(s) | Phase |
|---|---|---|
| Ciona (Cao 2019) | iniG (initial gastrula), midG (middle gastrula) | gastrula |
| | earN (early neurula), latN (late neurula) | neurula |
| | iniTI, earTI, midTII, latTI, latTII (tailbud) | organogenesis |
| | larva (swimming tadpole) | organogenesis |
| Amphioxus (Markos 2024) | G4 (mid-gastrula) | gastrula |
| | N0, N2, N5 (early → late neurula) | neurula |

### Boundary calls — probe species

- **Macaque inherits the human Carnegie convention; the only new call is CS11 → neurula (judgment call).** CS8–CS10 → neurula is already resolved for human (CS8 neural plate, CS9 1–3 somites, CS10 4–12 somites, neural-fold fusion — [O'Rahilly & Müller 1987, Carnegie Publ. 637](https://www.ehd.org/developmental-stages/stage10.php)). CS11 is 13–20 somites with the rostral neuropore closing (~24 ± 1 postovulatory days; [stage 11](https://www.ehd.org/developmental-stages/stage11.php)) and sits between CS10 (neurula) and CS12 (organogenesis onset in the human table). Assigning CS11 → neurula keeps the primate Carnegie axis internally consistent; the alternative (organogenesis, by somite-count analogy with mouse E9.5) is absorbed by the pre-registered one-bin sensitivity shift. Note: the Zhai dataset's own `theiler_stage` annotation maps E20 → CS8, E23 → CS9, E26 and E29 → CS11 — no CS10 embryos exist in the file despite the "CS8–CS11" dataset name.
- **Macaque ex utero ME-days (weakest anchor in this section — judgment call).** [Gong et al. 2023, Cell](https://pubmed.ncbi.nlm.nih.gov/37172563/) cultured cynomolgus embryos ex utero to 25 days post-fertilization; terminal embryos (d.p.f. 23–25) match in vivo CS8 morphology ([Liu et al. 2023, Cell](https://www.cell.com/cell/pdf/S0092-8674(23)00794-8.pdf): "ex vivo cultured d.p.f. 23–25 (equivalent to Carnegie Stage 8)"), i.e. a ~3–5 day lag versus in vivo (E20 = CS8). Interpolating along the Carnegie axis: ME18–ME20 ≈ CS6–7 (gastrulation) → gastrula; ME21–ME25 ≈ CS7–8 → neurula. The ME20|ME21 boundary is genuinely uncertain (any of ME21–23 could still be CS7); flagged for the sensitivity shift rather than resolved by literature.
- **Pig E13|E13.5 gastrula → neurula (judgment call).** [Simpson et al. 2024, Nat Commun](https://doi.org/10.1038/s41467-024-49407-6) stage the series as early-streak → 10-somite, "equivalent to Carnegie stages CS6 to CS10". The node emerges at E12.5 ("start of secondary gastrulation"), ectodermal/neural expansion begins at E13.5, first mature somites at E14, and E13 epiblast/streak cells morphologically mirror a human CS7/8 embryo. Under the project convention (CS6–7 → gastrula, CS8–10 → neurula) the boundary falls at E13|E13.5; the uncertain window is E12.5–E13.5, covered by the sensitivity shift. No pig timepoint reaches organogenesis (E15 ≈ CS10 ≈ mouse E8.5).
- **Guinea pig: no boundary.** All six `stage` classes are preimplantation (8-cell → late blastocyst, E3.5–E6; gastrulation begins well after implantation in this species) in [Canizo et al. 2025, Nat Cell Biol](https://doi.org/10.1038/s41556-025-01642-9). The coarse vocabulary has no cleavage/morula bin, so morula stages (8C, 16C, 16-32 cell) fold into blastula — the same precedent as mouse TOME E3.5–E5.5 → blastula.
- **Xenopus NF 13|14 gastrula → neurula (minor judgment call); the other two boundaries are anchored by the source paper itself.** NF stages 10–13 are gastrula (13 = late gastrula) and 14–21 neurula per the [Nieuwkoop & Faber normal table](https://www.xenbase.org/anatomy/static/NF/NF1-10.jsp) ([Zahn et al. 2022, Development 149:dev200356](https://doi.org/10.1242/dev.200356)); some secondary sources start the neurula at 13, so S13|14 is the flagged bin. Stage_8 → blastula and Stage_22 → organogenesis are anchored by [Briggs et al. 2018, Science](https://doi.org/10.1126/science.aar5780) themselves: samples span "zygotic genome activation (stage 8, 5 hpf) through early organogenesis (stage 22, 22 hpf)" (NF 22 = early tailbud, mapped to organogenesis rather than neurula because organ primordia are forming; phylotypic-alignment alternative is neurula — flagged).
- **Ciona tailbud onset → organogenesis (judgment call).** Ciona is an invertebrate *chordate* with true neurulation, so the named neurula stages (earN, latN) map to `neurula` directly — the "no true neurula" convention is not invoked. Staging follows [Hotta et al. 2007, Dev Dyn 236:1790–1805](https://doi.org/10.1002/dvdy.21188) (the developmental table [Cao et al. 2019, Nature](https://doi.org/10.1038/s41586-019-1385-y) raised embryos by). Tailbud stages (iniTI–latTII) are the trunk/tail morphogenesis and organ-rudiment period → organogenesis, paralleling the Xenopus NF-22 call; `larva` (swimming tadpole) is post-hatching with all larval tissues formed and folds into organogenesis as the least-bad bin (flagged: arguably post-embryonic).
- **Amphioxus: no boundary call.** [Markos et al. 2024, Nat Commun](https://doi.org/10.1038/s41467-024-52938-7) define the series themselves as "mid-gastrula to neurula stages (G4, N0, N2 and N5)"; the G/N nomenclature derives from the Hirakow & Kajita EM staging of amphioxus ([1991, J Morphol 207:37–52, the gastrula](https://pubmed.ncbi.nlm.nih.gov/29865496/); [1994, the neurula and larva](https://pubmed.ncbi.nlm.nih.gov/8178614/)). Like Ciona, amphioxus is a chordate with true neurulation, so N0/N2/N5 → neurula is not the invertebrate phylotypic convention but a direct mapping.
- **Provenance flag (not a phase call):** the local README for the Gong ex-utero H5AD cites DOI 10.1016/j.cell.2023.06.018; the verified DOI is [10.1016/j.cell.2023.04.020](https://pubmed.ncbi.nlm.nih.gov/37172563/) (Cell 186:2092–2110.e23, PMID 37172563). The README should be corrected when the manifest entries are written.

### Source publications (verified)

- Macaque CS8–CS11 sc: [Zhai et al. 2022, Nature 612:732–738](https://doi.org/10.1038/s41586-022-05526-y) — six CS8–CS11 cynomolgus embryos, E20–E29.
- Macaque ex utero: [Gong et al. 2023, Cell 186:2092–2110.e23](https://pubmed.ncbi.nlm.nih.gov/37172563/) — blastocyst → early organogenesis ex utero, ME18–ME25.
- Macaque CS9–CS10 spatial: [A three-dimensional spatial transcriptome atlas reconstructs early organogenesis in primate Carnegie stages 9 and 10 embryos, Nat Cell Biol 2026](https://www.nature.com/articles/s41556-026-01956-2).
- Pig: [Simpson et al. 2024, Nat Commun 15:5210](https://doi.org/10.1038/s41467-024-49407-6) — 91,232 cells, 62 embryos, E11.5–E15.
- Guinea pig: [Canizo, Zhao & Petropoulos 2025, Nat Cell Biol 27:696–710](https://doi.org/10.1038/s41556-025-01642-9) — preimplantation, E3.5–E6.
- Xenopus: [Briggs et al. 2018, Science 360:eaar5780](https://doi.org/10.1126/science.aar5780) — 136,966 cells, NF stages 8–22.
- Ciona: [Cao et al. 2019, Nature 571:349–354](https://doi.org/10.1038/s41586-019-1385-y) — initial gastrula → swimming tadpole, staged per Hotta et al. 2007.
- Amphioxus: [Markos et al. 2024, Nat Commun 15:8859](https://doi.org/10.1038/s41467-024-52938-7) — G4, N0, N2, N5 (mid-gastrula → late neurula).
