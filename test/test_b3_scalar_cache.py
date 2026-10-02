"""Public scalar-cache experiment on actual prepared rows and small Torch heads."""

import json
from pathlib import Path
import pytest

pytest_plugins = ("test.test_b3_pilot_shard_handoff",)


@pytest.fixture
def native_float32_pilot(request, monkeypatch):
    import test.test_b3_pilot_shard_handoff as boundary

    class Float32SoftcapHead(boundary.SmallGeneModel):
        def __init__(self, width):
            super().__init__(width)
            self.gene_id_criterion.softcap = 4.0

        def forward(self, *, batch, embed=False):
            output = super().forward(batch=batch, embed=embed)
            output["gene_logit"] = output["gene_logit"].float()
            return output

    monkeypatch.setattr(boundary, "SmallGeneModel", Float32SoftcapHead)
    return request.getfixturevalue("native_pilot")


def _reconciled_replay(native_pilot, tmp_path):
    from scripts.import_b3_measured_zero_pilot_shard import run as import_pilot
    from scripts.reconcile_b3_measured_zero_full_shard import reconcile
    from scripts.replay_b3_measured_zero_native_effects import run as replay

    plan, bundle = native_pilot
    handoff = tmp_path / "handoff"
    import_pilot(plan, bundle, handoff)
    certificate = tmp_path / "certificate.json"
    reconcile(plan, handoff / "shards", 0, handoff / "provenance.json", certificate)
    previous = tmp_path / "native_replay.json"
    replay(
        plan,
        handoff / "shards",
        handoff / "provenance.json",
        certificate,
        previous,
        cell_indices=[0],
        deletions_per_cell=2,
        execute=True,
        device="cpu",
    )
    return plan, handoff / "shards", handoff / "provenance.json", certificate, previous


def test_scalar_cache_matches_native_scores_and_terminal_unavailability(native_pilot, tmp_path):
    from scripts.study_b3_scalar_cache import run

    inputs = _reconciled_replay(native_pilot, tmp_path)
    output = tmp_path / "cache_study.json"
    report = run(*inputs, output, scored_deletions_per_cell=2, execute=True, device="cpu")
    assert report["status"] == "scalar_cache_equivalence_passed"
    assert report["model_forward_count"] == 7
    scored = [r for r in report["comparisons"] if r["status"] == "scored"]
    assert [r["token_position"] for r in scored] == [0, 50]
    assert [r["n_targets"] for r in scored] == [51, 1]
    assert max(r["cache_native_error_bits"] for r in scored) == 0
    terminal = [r for r in report["comparisons"] if r["status"] == "no_matched_target"]
    assert len(terminal) == 1 and terminal[0]["impact_bits"] is None
    assert report["cache_dtype"] == "torch.float64"
    assert report["all_shard_effects_attested"] is False
    assert report["scientific_readiness"] == "unavailable_diagnostic_subset_only"
    assert json.loads(output.read_text()) == report


def test_cache_keeps_native_float32_dtype_with_nonzero_softcap(native_float32_pilot, tmp_path):
    from scripts.study_b3_scalar_cache import run

    inputs = _reconciled_replay(native_float32_pilot, tmp_path)
    report = run(*inputs, tmp_path / "float32_study.json", scored_deletions_per_cell=2, execute=True, device="cpu")
    assert report["cache_dtype"] == "torch.float32"
    assert max(row["cache_native_error_bits"] for row in report["comparisons"] if row["status"] == "scored") == 0


def test_cache_study_rejects_replay_cell_selection_inconsistent_with_its_checks(native_pilot, tmp_path):
    from scripts.study_b3_scalar_cache import run

    inputs = _reconciled_replay(native_pilot, tmp_path)
    replay_path = inputs[-1]
    replay = json.loads(replay_path.read_text())
    replay["cell_indices"] = [1]
    replay_path.write_text(json.dumps(replay))
    output = tmp_path / "unreviewed_cell.json"
    with pytest.raises(ValueError, match="replay|subset"):
        run(*inputs, output, scored_deletions_per_cell=2, execute=True, device="cpu")
    assert not output.exists()


@pytest.mark.parametrize("failure", ["nonfinite", "inconsistent_error"])
def test_cache_study_rejects_inconsistent_independent_replay_impacts(native_pilot, tmp_path, failure):
    from scripts.study_b3_scalar_cache import run

    inputs = _reconciled_replay(native_pilot, tmp_path)
    replay_path = inputs[-1]
    replay = json.loads(replay_path.read_text())
    contrast = replay["contrasts"][0]
    if failure == "nonfinite":
        contrast["independent_reference_impact_bits"] = float("nan")
    else:
        contrast["independent_reference_impact_bits"] += 0.1
    replay_path.write_text(json.dumps(replay))
    output = tmp_path / "invalid_replay_impact.json"
    with pytest.raises(ValueError, match="effect evidence"):
        run(*inputs, output, scored_deletions_per_cell=2, execute=True, device="cpu")
    assert not output.exists()


def test_cache_study_rejects_replay_mutation_after_it_was_parsed(native_pilot, tmp_path, monkeypatch):
    from scripts.study_b3_scalar_cache import run

    inputs = _reconciled_replay(native_pilot, tmp_path)
    replay_path = inputs[-1]
    replacement = json.loads(replay_path.read_text())
    replacement["contrasts"][0]["independent_reference_impact_bits"] = float("nan")
    original_open = Path.open
    changed = False

    def change_replay_during_weight_hash(path, *args, **kwargs):
        nonlocal changed
        if not changed and path.name == "model_weights.pt" and args and args[0] == "rb":
            changed = True
            replay_path.write_text(json.dumps(replacement))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", change_replay_during_weight_hash)
    output = tmp_path / "mutated_replay.json"
    with pytest.raises(ValueError, match="replay.*changed"):
        run(*inputs, output, scored_deletions_per_cell=2, execute=True, device="cpu")
    assert changed and not output.exists()
