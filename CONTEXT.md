# Zebrafish Embryo Finetuning

Finetuning the TranscriptFormer Metazoa checkpoint on zebrafish embryo development data so the resulting model can be used to study cellular development and regulation.

## Language

**Zebrafish embryo**:
The developmental-stage-resolved embryo data of *Danio rerio*, the species used for finetuning.
_Avoid_: zebra embryo, zebra fish

**Metazoa checkpoint**:
The pretrained TranscriptFormer model checkpoint for the twelve-species Metazoa model, including in-vocabulary *Danio rerio* gene embeddings.
_Avoid_: metazoa model, the metazoa

**Independent embryo datasets**:
Single-cell and spatial transcriptome datasets treated as separate collections with no assumed cell- or section-level correspondence between them.
_Avoid_: matched datasets, paired datasets

**Spatial spot**:
The observation unit of the spatial transcriptomics dataset, treated as a pseudo-cell with its measured gene-expression counts, without assuming it is a single cell.
_Avoid_: spatial cell, spot-cell

**Spatial coordinates**:
The x/y (or section-level) positions of spatial spots, preserved as metadata in `.obs` for downstream spatial analysis, not consumed as model input during finetuning.
_Avoid_: spatial input, position features

**Developmental stage label**:
The embryo-stage metadata for a cell or spatial spot (hpf, somite stage, or standardized stage name), which must be harmonized into one vocabulary across both datasets before training.
_Avoid_: timepoint, stage column

**Cell type annotation**:
The cell-type label assigned to a cell or spatial spot, used for downstream evaluation and label harmonization rather than as a finetuning supervision target.
_Avoid_: cell type target, classification label

**Raw count matrix**:
The unnormalized UMI or transcript counts used as model input; normalized or log-transformed matrices are not accepted without rebuilding from raw quantification.
_Avoid_: normalized counts, log counts

**Model-ready H5AD**:
The standardized input format for finetuning: an AnnData H5AD with `var.ensembl_id` containing `ENSDARG...` IDs and a raw count matrix in `.X` or `.raw.X`.
_Avoid_: processed H5AD, cleaned data

**Raw spot counts**:
The spatial spot-level count matrix used directly as pseudo-cell training input, with deconvolution left as an optional downstream extension rather than a training-time preprocessing step.
_Avoid_: deconvolved spots, spot cell-type fractions

**Generative finetuning**:
Continuing the model's original gene/count prediction objective on the embryo datasets, rather than training a supervised task head.
_Avoid_: supervised finetuning, classification finetuning

**Dataset-balanced sampling**:
Mixing single-cell and spatial observations in each training batch so the smaller spatial modality contributes meaningfully despite the ~30M-cell single-cell side.
_Avoid_: natural weighting, proportional sampling

**Final holdout**:
Embryos and spatial sections never used for training, early stopping, or checkpoint selection; they are reserved for the final evaluation metrics.
_Avoid_: test split, validation split
