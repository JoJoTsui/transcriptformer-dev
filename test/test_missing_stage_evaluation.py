"""Missing stages must not influence the pseudotime trajectory or score."""

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from transcriptformer.finetune.evaluate import pseudotime_stage_spearman


def _trajectory(stages, species=None):
    obs = pd.DataFrame({"stage": stages}, index=[str(i) for i in range(len(stages))])
    if species is not None:
        obs["species"] = species
    data = ad.AnnData(obs=obs)
    data.obsm["embeddings"] = np.column_stack([np.arange(len(stages)), np.zeros(len(stages))])
    return data


@pytest.mark.parametrize("sentinel", [np.nan, None, pd.NA, "", "nan", "None", "<NA>", " UnKnOwN "])
def test_missing_stage_embeddings_do_not_change_score(sentinel):
    stages = ["blastula"] * 10 + ["gastrula"] * 10
    original = _trajectory(stages)
    extended = _trajectory(stages + [sentinel] * 5)
    extended.obsm["embeddings"][-5:] = np.random.default_rng(5).normal(size=(5, 2)) * 100
    before = extended.copy()
    expected = pseudotime_stage_spearman(original)
    result = pseudotime_stage_spearman(extended)

    assert np.isfinite(expected["spearman"])
    assert result["spearman"] == expected["spearman"]
    assert result["n_stages"] == 2
    assert result["n_input_obs"] == 25
    assert result["n_obs"] == result["n_evaluated_obs"] == 20
    assert result["n_obs_missing_stage"] == 5
    pd.testing.assert_frame_equal(extended.obs, before.obs)
    np.testing.assert_array_equal(extended.obsm["embeddings"], before.obsm["embeddings"])


@pytest.mark.parametrize(
    ("stages", "reason", "n_valid"),
    [([None, "unknown", np.nan], "no_known_stages", 0), ([0, 0, None], "too_few_stages", 2)],
)
def test_unevaluable_stage_counts(stages, reason, n_valid):
    result = pseudotime_stage_spearman(_trajectory(stages))
    assert np.isnan(result["spearman"])
    assert result["reason"] == reason
    assert result["n_obs"] == n_valid
    assert result["n_evaluated_obs"] == 0
    assert result["n_obs_missing_stage"] == len(stages) - n_valid


def test_grouped_stages_report_counts_and_unevaluable_reasons():
    data = _trajectory(
        [0, 0, 1, 1, None, "unknown", "gastrula", "gastrula", None, 2],
        ["a"] * 5 + ["b"] + ["c"] * 3 + [None],
    )
    result = pseudotime_stage_spearman(data)
    assert np.isfinite(result["spearman"])
    assert result["n_input_obs"] == 10
    assert result["n_obs"] == 6
    assert result["n_evaluated_obs"] == 4
    assert result["n_obs_missing_stage"] == 3
    assert result["n_obs_missing_group"] == 1
    assert result["n_groups_evaluated"] == 1
    assert result["n_groups_unevaluable"] == 2
    assert result["per_group"]["a"]["n_obs_missing_stage"] == 1
    assert result["per_group"]["b"]["reason"] == "no_known_stages"
    assert result["per_group"]["c"]["reason"] == "too_few_stages"
    assert result["unevaluable_reason_counts"] == {"no_known_stages": 1, "too_few_stages": 1}
