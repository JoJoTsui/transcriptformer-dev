import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.probes import audit_probe_dataset, map_probe_stages


def test_mapping_preserves_native_and_does_not_mutate():
    obs = pd.DataFrame({"age": ["E20", "E29"]})
    result = map_probe_stages(obs, "age", {"E20": "neurula", "E29": "neurula"})
    assert result.native_stage.tolist() == ["E20", "E29"]
    assert result.stage.tolist() == ["neurula", "neurula"]
    assert list(obs.columns) == ["age"]


@pytest.mark.parametrize("stages", [["E99"], [None], [""], [float("nan")]])
def test_mapping_rejects_unknown_or_missing(stages):
    with pytest.raises(ValueError, match="Unmapped"):
        map_probe_stages(pd.DataFrame({"stage": stages}), "stage", {"E20": "neurula"})


def test_mapping_rejects_missing_column_and_invalid_phase():
    with pytest.raises(ValueError, match="Missing stage"):
        map_probe_stages(pd.DataFrame(), "stage", {})
    with pytest.raises(ValueError, match="unsupported"):
        map_probe_stages(pd.DataFrame({"stage": ["E20"]}), "stage", {"E20": "invented"})


def make_source(tmp_path, species="Macaca fascicularis", stages=("E20",), missing_code=False):
    path = tmp_path / "source.h5ad"
    with h5py.File(path, "w") as f:
        # Deliberately no X: readiness must read only obs.
        obs = f.create_group("obs")
        obs.attrs["_index"] = "_index"
        obs.create_dataset("_index", data=np.array(["cell"], dtype="S"))
        cat = obs.create_group("stage")
        cat.create_dataset("categories", data=np.array(stages, dtype="S"))
        cat.create_dataset("codes", data=[-1 if missing_code else 0])
        for k, values in [
            ("species", [species]),
            ("cell_type", ["neural"]),
            ("embryo", ["embryo1"]),
            ("assay", ["10x 3' v3"]),
        ]:
            obs.create_dataset(k, data=np.array(values, dtype="S"))
    with h5py.File(tmp_path / "macaca_fascicularis_gene.h5", "w") as f:
        f.create_dataset("keys", data=np.array(["gene1"], dtype="S"))
        f.create_group("arrays").create_dataset("gene1", data=np.zeros(2560))
    entry = {
        "id": "probe",
        "species": "macaca_fascicularis",
        "path": str(path),
        "stage_column": "stage",
        "stage_mapping": {"E20": "neurula"},
        "metadata_columns": {"cell_type": "cell_type", "embryo_id": "embryo", "assay": "assay"},
    }
    return entry


def audit(tmp_path, entry, fasta_species="macaca_fascicularis"):
    return audit_probe_dataset(
        entry, {fasta_species: {"fa": f"https://example.test/{fasta_species}/pep.fa"}}, tmp_path, tmp_path
    )


def test_valid_metadata_only_probe(tmp_path):
    report = audit(tmp_path, make_source(tmp_path))
    assert report["ready"]
    assert report["phase_counts"] == {"neurula": 1}


def test_species_identity_is_not_interchangeable(tmp_path):
    report = audit(tmp_path, make_source(tmp_path, species="Macaca mulatta"))
    assert any("Species metadata disagrees" in b for b in report["blockers"])
    entry = make_source(tmp_path)
    report = audit(tmp_path, entry, fasta_species="macaca_mulatta")
    assert any("Missing FASTA" in b for b in report["blockers"])


@pytest.mark.parametrize("kwargs", [{"stages": ("E99",)}, {"missing_code": True}])
def test_audit_records_unknown_and_missing(tmp_path, kwargs):
    report = audit(tmp_path, make_source(tmp_path, **kwargs))
    assert not report["ready"]
    assert report["unknown_stage_counts"] or report["missing_stage_count"]


def test_missing_metadata_and_assets_are_explicit(tmp_path):
    entry = make_source(tmp_path)
    entry["metadata_columns"] = {}
    entry["species_column"] = "absent"
    report = audit_probe_dataset(entry, {}, tmp_path / "absent", tmp_path)
    assert not report["ready"]
    assert len(report["blockers"]) == 6


def test_documented_mapping_inventory():
    config = json.loads((Path(__file__).resolve().parents[1] / "preprocess/probe_stage_mappings.json").read_text())
    entries = {e["id"]: e for e in config["datasets"]}
    assert len(entries) == 8
    assert len({e["species"] for e in entries.values()}) == 6
    assert entries["macaque_zhai_2022"]["stage_mapping"] == dict.fromkeys(["E20", "E23", "E26", "E29"], "neurula")
    assert entries["xenopus_briggs_2018"]["stage_mapping"]["Stage_22"] == "organogenesis"
    assert entries["macaque_gong_2023"]["stage_mapping"]["ME20"] == "gastrula"
    assert entries["macaque_gong_2023"]["stage_mapping"]["ME21"] == "neurula"
