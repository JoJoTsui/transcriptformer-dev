"""Shared B3 scheduling at the public iterator seam."""

import pytest


def test_diagnostic_schedule_matches_literal_frozen_weights():
    from scripts.b3_streamed_draw_schedule import iter_diagnostic_draw_weights

    draws = list(
        iter_diagnostic_draw_weights(
            {"/z/mouse": ["b4", "b2", "b0", "b3", "b1"], "/a/human": ["a4", "a1", "a3", "a0", "a2"]},
            start=0,
            stop=1,
        )
    )
    assert len(draws) == 1
    assert draws[0].as_dict() == {
        "index": 0,
        "scope": "diagnostic_descriptive",
        "weights": {
            "/a/human": {"a0": 0, "a1": 1, "a2": 1, "a3": 2, "a4": 1},
            "/z/mouse": {"b0": 2, "b1": 0, "b2": 1, "b3": 1, "b4": 1},
        },
        "effective_embryos": {"/a/human": 4, "/z/mouse": 4},
    }


@pytest.mark.parametrize("start,stop", [(True, 1), (0, 1.0), (-1, 1), (1, 1), (0, 101), (1999, 2001)])
def test_diagnostic_schedule_rejects_invalid_shard_indices(start, stop):
    from scripts.b3_streamed_draw_schedule import iter_diagnostic_draw_weights

    with pytest.raises(ValueError, match="draw shard"):
        list(iter_diagnostic_draw_weights({"/a": ["e0", "e1"]}, start=start, stop=stop))


@pytest.mark.parametrize(
    "sources",
    [
        {},
        {"relative": ["e0"]},
        {"/a/../b": ["e0"]},
        {"/a": []},
        {"/a": "e0"},
        {"/a": ["e0", "e0"]},
        {"/a": [" e0"]},
        {"/a": [1]},
        {f"/source{i}": ["e0"] for i in range(33)},
    ],
)
def test_diagnostic_schedule_rejects_invalid_source_or_embryo_axes(sources):
    from scripts.b3_streamed_draw_schedule import iter_diagnostic_draw_weights

    with pytest.raises(ValueError, match="(?i)source|embryo"):
        list(iter_diagnostic_draw_weights(sources, start=0, stop=1))


def _plan():
    return {
        "schema": "b3_measured_zero_bootstrap_plan_v1",
        "seed": 20260930,
        "draws_required": 2000,
        "source_bundles": {
            "/unused": {"embryos": [f"u{i}" for i in range(5)], "species": "unused", "phase": "organogenesis"},
            "/z/mouse": {"embryos": [f"b{i}" for i in range(5)], "species": "mouse", "phase": "organogenesis"},
            "/a/human": {"embryos": [f"a{i}" for i in range(5)], "species": "human", "phase": "organogenesis"},
        },
        "comparisons": [
            {
                "comparison_id": "human_mouse",
                "bundle_a": "/a/human",
                "bundle_b": "/z/mouse",
                "species_a": "human",
                "species_b": "mouse",
                "phase": "organogenesis",
                "status": "bootstrap_eligible",
                "n_joined_pairs": 625,
                "n_fixed_pairs": 500,
                "fixed_pairs": [[f"h{i}", f"m{i}"] for i in range(500)],
                "rho_observed": 0.8,
            },
            {
                "comparison_id": "unavailable_mouse_unused",
                "bundle_a": "/z/mouse",
                "bundle_b": "/unused",
                "status": "unavailable_original_coverage_or_embryos",
            },
        ],
    }


def test_production_schedule_excludes_unavailable_comparison_sources():
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    draw = next(iter_bootstrap_draw_weights(_plan(), start=0, stop=1))
    assert draw.scope == "bootstrap_production"
    assert draw.as_dict()["weights"] == {
        "/a/human": {"a0": 0, "a1": 1, "a2": 1, "a3": 2, "a4": 1},
        "/z/mouse": {"b0": 2, "b1": 0, "b2": 1, "b3": 1, "b4": 1},
    }


@pytest.mark.parametrize(
    "field,value",
    [("schema", "wrong"), ("seed", True), ("seed", 1), ("draws_required", 2000.0), ("draws_required", 2001)],
)
def test_production_schedule_rejects_changed_plan_protocol(field, value):
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    plan[field] = value
    with pytest.raises(ValueError):
        list(iter_bootstrap_draw_weights(plan, start=0, stop=1))


@pytest.mark.parametrize("field,value", [("n_fixed_pairs", 499), ("n_joined_pairs", 626), ("n_fixed_pairs", 500.0)])
def test_production_schedule_rejects_unsupported_eligibility(field, value):
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    plan["comparisons"][0][field] = value
    with pytest.raises(ValueError):
        list(iter_bootstrap_draw_weights(plan, start=0, stop=1))


def test_production_schedule_requires_five_original_independent_embryos():
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    plan["source_bundles"]["/a/human"]["embryos"] = ["a0", "a1", "a2", "a3"]
    with pytest.raises(ValueError):
        list(iter_bootstrap_draw_weights(plan, start=0, stop=1))


@pytest.mark.parametrize(
    "change", ["duplicate_id", "unknown_status", "same_source", "empty_id", "duplicate_pair", "phase"]
)
def test_production_schedule_rejects_inconsistent_comparison_identity(change):
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    comparison = plan["comparisons"][0]
    if change == "duplicate_id":
        plan["comparisons"][1]["comparison_id"] = comparison["comparison_id"]
    elif change == "unknown_status":
        plan["comparisons"][1]["status"] = "unknown"
    elif change == "same_source":
        comparison["bundle_b"] = comparison["bundle_a"]
    elif change == "empty_id":
        comparison["comparison_id"] = ""
    elif change == "duplicate_pair":
        comparison["fixed_pairs"][1][1] = comparison["fixed_pairs"][0][1]
    else:
        plan["source_bundles"]["/z/mouse"]["phase"] = "fetal"
    with pytest.raises(ValueError):
        list(iter_bootstrap_draw_weights(plan, start=0, stop=1))


def test_restart_and_reordered_axes_preserve_literal_later_draw():
    from scripts.b3_streamed_draw_schedule import iter_diagnostic_draw_weights

    sources = {"/a/human": [f"a{i}" for i in range(5)], "/z/mouse": [f"b{i}" for i in range(5)]}
    uninterrupted = list(iter_diagnostic_draw_weights(sources, start=0, stop=4))
    reordered = {path: list(reversed(embryos)) for path, embryos in reversed(list(sources.items()))}
    restarted = list(iter_diagnostic_draw_weights(reordered, start=2, stop=4))
    assert [draw.as_dict() for draw in restarted] == [draw.as_dict() for draw in uninterrupted[2:]]
    assert restarted[1].as_dict()["weights"] == {
        "/a/human": {"a0": 1, "a1": 0, "a2": 1, "a3": 1, "a4": 2},
        "/z/mouse": {"b0": 0, "b1": 2, "b2": 1, "b3": 0, "b4": 2},
    }


def test_shared_source_is_sampled_once_across_eligible_comparisons():
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    plan["comparisons"][1] = {
        "comparison_id": "human_unused",
        "bundle_a": "/a/human",
        "bundle_b": "/unused",
        "species_a": "human",
        "species_b": "unused",
        "phase": "organogenesis",
        "status": "bootstrap_eligible",
        "n_joined_pairs": 625,
        "n_fixed_pairs": 500,
        "fixed_pairs": [[f"h{i}", f"u{i}"] for i in range(500)],
    }
    draw = next(iter_bootstrap_draw_weights(plan, start=0, stop=1))
    assert draw.as_dict()["weights"] == {
        "/a/human": {"a0": 0, "a1": 1, "a2": 1, "a3": 2, "a4": 1},
        "/unused": {"u0": 2, "u1": 0, "u2": 1, "u3": 1, "u4": 1},
        "/z/mouse": {"b0": 2, "b1": 0, "b2": 0, "b3": 2, "b4": 1},
    }
    assert draw.effective_embryos["/a/human"] == 4


def test_yielded_weights_are_immutable_and_caller_inputs_are_snapshotted():
    from dataclasses import FrozenInstanceError

    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    iterator = iter_bootstrap_draw_weights(plan, start=0, stop=2)
    first = next(iterator)
    with pytest.raises(TypeError):
        first.weights["/other"] = {}
    with pytest.raises(TypeError):
        first.weights["/a/human"]["a0"] = 9
    with pytest.raises(TypeError):
        first.effective_embryos["/a/human"] = 9
    with pytest.raises(FrozenInstanceError):
        first.index = 10
    copied = first.as_dict()
    copied["weights"]["/a/human"]["a0"] = 9
    assert first.weights["/a/human"]["a0"] == 0
    plan["source_bundles"]["/a/human"]["embryos"].clear()
    assert next(iterator).as_dict()["weights"] == {
        "/a/human": {"a0": 2, "a1": 0, "a2": 0, "a3": 2, "a4": 1},
        "/z/mouse": {"b0": 1, "b1": 1, "b2": 0, "b3": 1, "b4": 2},
    }


def test_wholly_unavailable_family_cannot_schedule_production():
    from scripts.b3_streamed_draw_schedule import iter_bootstrap_draw_weights

    plan = _plan()
    plan["comparisons"][0]["status"] = "unavailable_original_coverage_or_embryos"
    with pytest.raises(ValueError, match="No family comparison"):
        list(iter_bootstrap_draw_weights(plan, start=0, stop=1))


def test_oversized_axis_is_rejected_before_iterating_or_allocating_identities():
    from collections.abc import Sequence

    from scripts.b3_streamed_draw_schedule import iter_diagnostic_draw_weights

    class OversizedAxis(Sequence):
        def __len__(self):
            return 100_001

        def __getitem__(self, index):
            raise AssertionError("Oversized axis must not be read")

    with pytest.raises(ValueError, match="metadata allocation bound"):
        list(iter_diagnostic_draw_weights({"/a": OversizedAxis()}, start=0, stop=1))
