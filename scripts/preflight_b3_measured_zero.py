#!/usr/bin/env python3
"""Necessary support for the approved measured-zero amendment; no model scores."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run(config_path):
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    import numpy as np
    import torch
    from transcriptformer.finetune.b3_bins import build_expression_dropout_bins
    from transcriptformer.finetune.b3_prepared import configured_prepared_cells
    from transcriptformer.finetune.b3_pipeline import file_sha256
    from transcriptformer.finetune.train import _dataset_kwargs
    torch.set_num_threads(1)
    config = json.loads(Path(config_path).read_text())
    cells, cfg, _, _ = configured_prepared_cells(config)
    try:
        if not bool(cfg.model.data_config.pad_zeros):
            raise ValueError('Measured-zero preflight requires native positive-token preprocessing')
        preprocessing = _dataset_kwargs(cfg)
        required = {'sort_genes': False, 'randomize_order': False, 'pad_zeros': True,
                    'filter_to_vocab': True, 'normalize_to_scale': 0, 'use_raw': None,
                    'remove_duplicate_genes': False, 'clip_counts': 30,
                    'gene_col_name': 'ensembl_id'}
        if any(preprocessing[key] != value for key, value in required.items()):
            raise ValueError('Measured-zero support requires the frozen native preprocessing')
        if float(cfg.model.data_config.filter_outliers) != 0 or int(cfg.model.data_config.min_expressed_genes) != 0:
            raise ValueError('Measured-zero support cannot change prepared cell membership')
        if len(cells.cells) * len(cells.gene_ids) > 10_000_000:
            raise ValueError('Bounded support exceeds ten million Boolean entries')
        metrics = cells.summarize()
        plan = build_expression_dropout_bins(metrics['metrics'])
        index = {g: i for i, g in enumerate(cells.gene_ids)}
        native = np.zeros((len(index), len(cells.cells)), dtype=bool)
        positive = np.zeros_like(native)
        eligible_target = np.zeros(len(cells.cells), dtype=bool)
        attempts = 0
        for cell_number, (identity, cell) in enumerate(zip(cells.cells, cells.iter_cells(), strict=True)):
            raw = cells.dataset._X_per_file[identity['file_index']][identity['row']]
            raw = raw.toarray().ravel() if hasattr(raw, 'toarray') else np.asarray(raw).ravel()
            if not np.isfinite(raw).all() or (raw < 0).any() or (raw != np.floor(raw)).any():
                raise ValueError('Invalid measured raw counts')
            positive[:, cell_number] = raw[cells.feature_indices[identity['file_index']]] > 0
            ids = cell.batch.gene_token_indices[0].tolist()
            counts = cell.batch.gene_counts[0].tolist()
            if len(ids) != int(cfg.model.model_config.seq_len):
                raise ValueError('Native sequence length differs')
            positions = [(p, cells.gene_names[int(t)]) for p, (t, c) in enumerate(zip(ids, counts, strict=True)) if c > 0]
            targets = [p for p, _ in positions if p < len(ids) - 1]
            eligible_target[cell_number] = bool(targets)
            last = targets[-1] if targets else -1
            for p, gene in positions:
                if not positive[index[gene], cell_number]:
                    raise ValueError('Native token contradicts measured raw counts')
                if p < last:
                    native[index[gene], cell_number] = True
            attempts += len(positions)
            if attempts > 100000:
                raise ValueError('Pilot exceeds unchanged 100000 positive deletion row cap')
        available = native | (~positive & eligible_target[None, :])
        by_bin = defaultdict(list)
        for gene, bin_id in plan.gene_bins.items():
            if bin_id is not None:
                by_bin[bin_id].append(index[gene])
        rows = []
        for gene, i in index.items():
            focal = native[i]
            peers = [j for j in by_bin[plan.gene_bins[gene]] if j != i and np.all(available[j, focal])] if focal.any() and plan.gene_bins[gene] is not None else []
            variable_peers = sum(bool(native[j, focal].any()) for j in peers)
            reason = ('no_potentially_scorable_cells' if not focal.any() else
                      'unavailable_sparse_dropout_band' if plan.gene_bins[gene] is None else
                      'fewer_than_two_potential_matched_peers' if len(peers) < 2 else
                      'all_peers_certified_zero' if not variable_peers else None)
            rows.append({'gene_id': gene, 'potentially_scorable_cells': int(focal.sum()),
                         'potential_full_support_bin_peers': len(peers),
                         'potential_nonzero_peers': variable_peers,
                         'necessary_conditions_met': reason is None,
                         'necessary_condition_failure': reason})
        return {'schema': 'b3_measured_zero_support_preflight_v1',
                'method': 'b3_measured_zero_peer_null_v2',
                'config_sha256': file_sha256(config_path),
                'input_sha256': {key: file_sha256(config[key]) for key in ('manifest', 'prepared_report', 'gene_vocabulary', 'aux_vocabulary')},
                'checkpoint_config_sha256': file_sha256(Path(config['checkpoint']) / 'config.json'),
                'cohort_sha256': cells.cohort_sha256, 'species': cells.species,
                'phase': cells.phase, 'split': cells.split, 'model_arm': cells.model_arm,
                'n_cells': len(cells.cells), 'n_embryos': len(metrics['embryo_metrics']),
                'normalization': cells.normalization, 'estimated_positive_raw_rows': attempts,
                'native_preprocessing': preprocessing,
                'possible_finite_score_upper_bound': sum(r['necessary_conditions_met'] for r in rows),
                'gene_support': rows, 'prepared_validation': cells.validation,
                'interpretation': 'Structural possibility only, not certified score evidence or positive variance',
                'model_forwards_performed': False, 'checkpoint_tensors_loaded': False}
    finally:
        cells.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = run(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('species', 'n_cells', 'possible_finite_score_upper_bound')}))


if __name__ == '__main__':
    main()
