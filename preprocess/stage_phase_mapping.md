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
