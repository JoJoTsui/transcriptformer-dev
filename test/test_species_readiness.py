"""Required species readiness uses validated prepared data and sampler exposure."""

import json
import pytest
import h5py
import anndata as ad

from test.fixtures import make_synthetic_h5ad
from transcriptformer.finetune.prepare import prepare_run
from transcriptformer.finetune.species_readiness import required_species_readiness


def _vocab(tmp_path):
    path = tmp_path / "fish_vocab.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("keys", data=[f"ENSDARG{i:011d}".encode() for i in range(1, 51)])
    return str(path)


def _checkpoint(tmp_path, genes):
    checkpoint = tmp_path / "checkpoint"
    (checkpoint / "vocabs").mkdir(parents=True)
    (checkpoint / "config.json").write_text(json.dumps({
        "model": {"data_config": {"esm2_mappings": ["danio_rerio_gene.h5"]}}
    }))
    with h5py.File(checkpoint / "vocabs" / "danio_rerio_gene.h5", "w") as handle:
        handle.create_dataset("keys", data=[gene.encode() for gene in genes])
    return checkpoint


def test_zebrafish_readiness_distinguishes_prepared_from_realized_training(tmp_path):
    fish = make_synthetic_h5ad(tmp_path / "fish.h5ad", n_obs=2, stage="fish")
    manifest = {"datasets": [{"path": str(fish), "species": "danio_rerio", "dataset_type": "single_cell", "vocab_path": _vocab(tmp_path)}]}
    checkpoint = _checkpoint(tmp_path, ["ENSDARG00000000001"])
    report = required_species_readiness(manifest, prepare_run(manifest, tmp_path / "prepared"), checkpoint_path=checkpoint)
    assert report["status"] == "prepared_ready_training_unverified"
    assert report["prepared_training_observations"] == 2
    assert report["positive_vocabulary_mapped_expression"]
    assert report["matched_prepared_gene_count"] == 1
    assert report["epoch_projection_draws"] > 0
    assert report["realized_training_draws"] is None
    assert report["realized_training_evidence"] == "unavailable_until_verified_training_run"


def test_zebrafish_readiness_blocks_missing_species(tmp_path):
    mouse = make_synthetic_h5ad(tmp_path / "mouse.h5ad", n_obs=2, stage="mouse")
    manifest = {"datasets": [{"path": str(mouse), "species": "mus_musculus", "dataset_type": "single_cell"}]}
    report = required_species_readiness(manifest, prepare_run(manifest, tmp_path / "prepared"), checkpoint_path=_checkpoint(tmp_path, ["ENSDARG00000000001"]))
    assert report["status"] == "blocked"
    assert "no_post_qc_training_observations" in report["reasons"]


def test_zebrafish_readiness_rejects_tampered_artifacts(tmp_path):
    fish = make_synthetic_h5ad(tmp_path / "fish.h5ad", n_obs=2)
    manifest = {"datasets": [{"path": str(fish), "species": "danio_rerio", "dataset_type": "single_cell", "vocab_path": _vocab(tmp_path)}]}
    prepared = prepare_run(manifest, tmp_path / "prepared")
    prepared["datasets"][0]["n_obs"] = 3
    with pytest.raises(ValueError):
        required_species_readiness(manifest, prepared, checkpoint_path=_checkpoint(tmp_path, ["ENSDARG00000000001"]))


def test_source_vocab_presence_does_not_substitute_for_checkpoint_join(tmp_path):
    fish = make_synthetic_h5ad(tmp_path / "fish.h5ad", n_obs=2)
    manifest = {"datasets": [{"path": str(fish), "species": "danio_rerio", "dataset_type": "single_cell", "vocab_path": _vocab(tmp_path)}]}
    prepared = prepare_run(manifest, tmp_path / "prepared")
    report = required_species_readiness(manifest, prepared, checkpoint_path=_checkpoint(tmp_path, ["OTHER_GENE"]))
    assert report["status"] == "blocked"
    assert "no_prepared_genes_in_checkpoint_vocabulary" in report["reasons"]


def test_positive_counts_outside_checkpoint_join_do_not_pass(tmp_path):
    fish = make_synthetic_h5ad(tmp_path / "fish.h5ad", n_obs=2)
    source = ad.read_h5ad(fish)
    source.X[:, 0] = 0
    source.X[:, 1] = 4
    source.write_h5ad(fish)
    manifest = {"datasets": [{"path": str(fish), "species": "danio_rerio", "dataset_type": "single_cell"}]}
    prepared = prepare_run(manifest, tmp_path / "prepared")
    report = required_species_readiness(manifest, prepared, checkpoint_path=_checkpoint(tmp_path, ["ENSDARG00000000001"]))
    assert report["status"] == "blocked"
    assert report["matched_prepared_gene_count"] == 1
    assert "no_positive_vocabulary_mapped_expression" in report["reasons"]


def test_checkpoint_join_passes_without_preparation_vocab_asset(tmp_path):
    fish = make_synthetic_h5ad(tmp_path / "fish.h5ad", n_obs=2)
    manifest = {"datasets": [{"path": str(fish), "species": "danio_rerio", "dataset_type": "single_cell"}]}
    prepared = prepare_run(manifest, tmp_path / "prepared")
    report = required_species_readiness(manifest, prepared, checkpoint_path=_checkpoint(tmp_path, ["ENSDARG00000000001"]))
    assert report["status"] == "prepared_ready_training_unverified"
