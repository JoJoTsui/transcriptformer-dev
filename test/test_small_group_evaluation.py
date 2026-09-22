"""Classification diagnostics remain defined on small or incomplete cohorts."""

import anndata as ad
import numpy as np
import pandas as pd

from transcriptformer.finetune.evaluate import cell_type_macro_f1


def test_two_members_per_class_get_valid_split():
    data = ad.AnnData(np.zeros((6, 1)), obs=pd.DataFrame({"cell_type": ["a", "a", "b", "b", "c", "c"]}))
    data.obsm["embeddings"] = np.repeat(np.eye(3), 2, axis=0)
    result = cell_type_macro_f1(data)
    assert result["macro_f1"] == 1.0
    assert result["n_train_obs"] == result["n_test_obs"] == 3


def test_missing_labels_and_singletons_are_accounted_without_mutation():
    labels = ["a", "a", "b", "b", "singleton", None, np.nan, " NaN ", "", "UNKNOWN", "<NA>"]
    data = ad.AnnData(np.zeros((len(labels), 1)), obs=pd.DataFrame({"cell_type": labels}))
    data.obsm["embeddings"] = np.arange(len(labels))[:, None]
    before = data.obs.copy(deep=True)
    result = cell_type_macro_f1(data)
    assert result["n_input_obs"] == 11
    assert result["n_obs_missing_label"] == 6
    assert result["n_obs_rare_class"] == 1
    assert result["n_obs"] == result["n_evaluated_obs"] == 4
    pd.testing.assert_frame_equal(data.obs, before)


def test_unevaluable_single_class_reports_reason():
    data = ad.AnnData(np.zeros((3, 1)), obs=pd.DataFrame({"cell_type": ["a", "a", "unknown"]}))
    data.obsm["embeddings"] = np.ones((3, 2))
    result = cell_type_macro_f1(data)
    assert np.isnan(result["macro_f1"])
    assert result["reason"] == "too_few_classes"
    assert result["n_evaluated_obs"] == 0


def test_imbalanced_rounding_preserves_all_classes_in_both_partitions():
    labels = np.repeat(["a", "b", "c", "d"], [7, 2, 2, 2])
    data = ad.AnnData(np.zeros((13, 1)), obs=pd.DataFrame({"cell_type": labels}))
    data.obsm["embeddings"] = np.repeat(np.eye(4), [7, 2, 2, 2], axis=0)
    result = cell_type_macro_f1(data)
    assert result["n_test_classes"] == result["n_train_classes"] == 4
    assert result["n_test_obs"] == 4
