# Multi-Species Embryogenesis Finetuning

Finetuning the TranscriptFormer Metazoa checkpoint on multi-species embryogenesis single-cell data so the resulting model can be used to study developmental regulation: phase-specific gene perturbation effects and cross-species comparison of regulation at the same developmental phase.

## Language

**Embryogenesis corpus**:
The collection of developmental-stage-resolved single-cell and spatial H5AD datasets under `/mnt/d/sc/data/scRNAseq-YBY/`, spanning multiple species, from which finetuning and downstream data are drawn.
_Avoid_: the data, YBY datasets

**Metazoa checkpoint**:
The pretrained TranscriptFormer TF-Metazoa model at `/mnt/d/sc/transcriptformer/checkpoints/tf_metazoa`, covering twelve species' gene vocabularies; the base for finetuning.
_Avoid_: metazoa model, the metazoa, base checkpoint

**Training species**:
The in-vocabulary embryogenesis species used for finetuning: human, mouse, zebrafish, chicken, rabbit, fruit fly, C. elegans, and sea urchin.
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
Sampling training batches in proportion to dataset size, matching the base model's own unbalanced pretraining; per-species balancing is a documented fallback, not the default.
_Avoid_: balanced sampling, equal weighting

**Final holdout**:
Embryos never used for training, early stopping, or checkpoint selection; reserved for the final evaluation metrics, assigned per species.
_Avoid_: test split, validation split

**Single-embryo dataset**:
A dataset measuring one embryo or spatial section (e.g. human CS7), assigned entirely to training because embryo-level splitting is impossible.
_Avoid_: unsplittable dataset

**Likelihood impact score**:
The drop in the model's predicted transcriptome likelihood for a cell when a gene is perturbed, used to rank gene × phase impact genome-wide.
_Avoid_: perturbation effect, gene importance

**Counterfactual generation**:
Regenerating the remainder of a cell's transcriptome after perturbing a gene, used to name predicted downstream-affected genes for top-ranked perturbations.
_Avoid_: in-silico knockout simulation, virtual perturbation
