# Multi-Species Embryogenesis Finetuning

Finetuning the TranscriptFormer Metazoa checkpoint on multi-species embryogenesis single-cell data so the resulting model can be used to study developmental regulation: phase-specific gene perturbation effects and cross-species comparison of regulation at the same developmental phase.

## Language

**Embryogenesis corpus**:
The collection of developmental-stage-resolved single-cell and spatial datasets spanning multiple species, from which finetuning and downstream data are drawn.
_Avoid_: the data, YBY datasets

**Metazoa checkpoint**:
The pretrained TranscriptFormer TF-Metazoa model, covering twelve species' gene vocabularies; the baseline for finetuning.
_Avoid_: metazoa model, the metazoa, base checkpoint

**Training species**:
The intended in-vocabulary embryogenesis species for finetuning: human, mouse, zebrafish, chicken, rabbit, fruit fly, C. elegans, and sea urchin.
_Avoid_: in-distribution species, finetune species

**Zero-shot probe species**:
Species with embryogenesis data that are never seen in finetuning and are reserved for downstream generalization tests: macaque, pig, guinea pig, Xenopus tropicalis, ciona, and amphioxus.
_Avoid_: out-of-distribution species, held-out species, test species

**Non-embryo datasets**:
Datasets in the corpus that do not measure embryogenesis (e.g. sponge juvenile, yeast culture, trichoplax, nematostella adult) and are excluded from the project entirely.
_Avoid_: junk data, unused data

**Developmental phase**:
A cross-species stage category from the coarse universal vocabulary (blastula, gastrula, neurula, organogenesis, fetal) that every native stage label maps into; the unit of "same phase" cross-species comparison.
_Avoid_: timepoint, stage, Carnegie stage

**Native stage label**:
The original per-dataset stage annotation (Carnegie stage, embryonic day, hpf, Nieuwkoop–Faber stage), preserved in `.obs` and mapped to a developmental phase via the manifest `stage_mapping`.
_Avoid_: raw stage, original timepoint

**Generative finetuning**:
Continuing the model's original gene/count prediction objective on the embryogenesis corpus, rather than training a supervised task head.
_Avoid_: supervised finetuning, classification finetuning

**Natural weighting**:
Equal per-observation sampling within a measurement modality; the approved mixture of single-cell and spatial observations determines their relative exposure. This does not imply equal species exposure.
_Avoid_: balanced sampling, equal weighting

**Final holdout**:
Embryos never used for training, early stopping, or checkpoint selection; reserved for the final evaluation metrics, assigned per species.
_Avoid_: test split, validation split

**Checkpoint-selection cohort**:
A fixed subset of validation embryos used for early stopping and checkpoint selection, covering the available developmental phases. Each evaluable species has equal weight, and embryos within each species have equal weight; this cohort is separate from the final holdout.
_Avoid_: final holdout, test cohort

**Single-embryo dataset**:
A dataset whose observations come from one physical embryo, assigned entirely to training when embryo-level splitting is impossible. Multiple spatial sections can belong to the same embryo.
_Avoid_: unsplittable dataset

**Gene-context impact**:
The original-minus-deleted change in mean log probability of matched downstream gene-ID targets, in bits per target, when a gene is removed from the model context. The focal gene’s own likelihood term is excluded.
_Avoid_: full-transcriptome likelihood drop, causal knockout effect, gene importance

**Counterfactual generation**:
Regenerating the remainder of a cell's transcriptome after perturbing a gene, used to name predicted downstream-affected genes for top-ranked perturbations.
_Avoid_: in-silico knockout simulation, virtual perturbation


**Physical embryo**:
The biological specimen that defines an independent embryo observation; cells and spatial sections from that specimen share its identity.
_Avoid_: section, file, cell as an independent embryo

**B3 null-corrected score**:
A descriptive z-score of embryo-balanced gene-context impact against complete peer genes matched by expression/dropout bins and the focal gene’s exact scored cells and embryos. Positive finite peer sample variance is required.
_Avoid_: causal effect, calibrated significance, FDR

**Observed paired coverage**:
The fraction of the frozen vocabulary-joined one-to-one ortholog universe with finite B3 scores in both species. Missing scores remain in the denominator.
_Avoid_: mapping coverage, percentage among scored pairs

**Structural support upper bound**:
The number of genes or ortholog pairs satisfying necessary support conditions before numerical effects and peer variance are known. It is a possibility bound, not observed paired coverage.
_Avoid_: completed comparison, finite score count

**Model arm**:
The baseline Metazoa checkpoint or a project finetuned checkpoint used for a specified comparison. A baseline-only result does not establish a benefit from finetuning.
_Avoid_: finetuned result when using baseline weights

**Project finetuned checkpoint**:
A checkpoint with documented embryo-corpus training provenance and checkpoint-selection evidence. Different weights or a directory label alone do not establish that provenance.
_Avoid_: candidate weights as a verified project model
