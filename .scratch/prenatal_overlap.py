"""Inter-file relationships + overlap of the prenatal time-lapse files vs the training mouse files.

- Sums n_obs across the 4 files (publication claims 11,441,407 nuclei).
- Pairwise obs_names overlap among the 4 big files (disjoint chunks vs replicates?).
- Per-file author_day / author_experimental_id distributions (already in prenatal_inspect.json).
- obs_names overlap against every mus_musculus file in conf/finetune_run_multispecies.json.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import json

import anndata as ad

OUT = "/mnt/d/sc/transcriptformer/transcriptformer/.scratch"
UUIDS = [
    "04912a4e-4fad-430b-9fd7-16d30c5c57fa",
    "3776b646-d6ae-4bd1-883f-5877e328b5ff",
    "4a321ccb-ec08-42bc-808f-167bbd1127d3",
    "aaf0497e-a8a9-4a81-8b22-c1ac86507c6b",
]

# --- totals from inspect json
info = json.load(open(f"{OUT}/prenatal_inspect.json"))
total = sum(v["n_obs"] for v in info.values())
print("total cells across 4 files:", total, "(publication claims 11,441,407)")
for k, v in info.items():
    print(f"  {k[:8]}: n_obs={v['n_obs']}")

# --- per-file day/run coverage comparison
import collections

day_union = collections.OrderedDict()
run_sets = {}
for k, v in info.items():
    days = v["obs_columns"]["author_day"]["value_counts_full"]
    day_union[k[:8]] = days
    runs = v["obs_columns"]["author_experimental_id"]["value_counts_full"]
    run_sets[k[:8]] = runs
all_days = sorted({d for m in day_union.values() for d in m})
print(f"\nauthor_day coverage per file ({len(all_days)} distinct days overall):")
hdr = "day".ljust(12) + "".join(k[:8].rjust(12) for k in day_union)
print(hdr)
for d in all_days:
    print(d.ljust(12) + "".join(str(m.get(d, 0)).rjust(12) for m in day_union.values()))
print("\nrun (author_experimental_id) coverage per file:")
all_runs = sorted({r for m in run_sets.values() for r in m}, key=lambda r: int(r.split("_")[1]))
print("run".ljust(12) + "".join(k[:8].rjust(12) for k in run_sets))
for r in all_runs:
    print(r.ljust(12) + "".join(str(m.get(r, 0)).rjust(12) for m in run_sets.values()))

# --- obs_names overlap among the 4 big files
print("\nloading obs_names sets ...", flush=True)
name_sets = {}
for u in UUIDS:
    with open(f"{OUT}/prenatal_obsnames/{u}.txt") as fh:
        name_sets[u] = set(fh.read().splitlines())
    print(f"  {u[:8]}: {len(name_sets[u])}")
uids = UUIDS
print("pairwise intersections:")
for i in range(4):
    for j in range(i + 1, 4):
        inter = len(name_sets[uids[i]] & name_sets[uids[j]])
        print(f"  {uids[i][:8]} & {uids[j][:8]}: {inter}")

# --- overlap vs training mouse files
manifest = json.load(open("/mnt/d/sc/transcriptformer/transcriptformer/conf/finetune_run_multispecies.json"))
mouse_files = [d["path"] for d in manifest["datasets"] if d["species"] == "mus_musculus"]
union_names = set().union(*name_sets.values())
del name_sets
print(f"\nunion of 4 big files: {len(union_names)} unique obs_names")
print("\noverlap vs training mus_musculus files (full obs_names of training file):")
for path in mouse_files:
    label = path.split("/")[-1]
    a = ad.read_h5ad(path, backed="r")
    try:
        names = list(a.obs_names)
    finally:
        a.file.close()
    s = set(names)
    inter = len(s & union_names)
    # also try stripped-barcode view: drop 'run_N_'-style prefixes? report raw first
    print(f"  {label[:80]}: n={len(names)}, raw-name overlap={inter} ({100*inter/max(len(s),1):.2f}%)")
    del names, s
