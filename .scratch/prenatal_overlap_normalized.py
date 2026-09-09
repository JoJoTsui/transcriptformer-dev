"""Normalized obs-name overlap: prenatal atlas vs training mouse files.

Prenatal obs_names look like `run_4_P2-01A.<barcode>-0`; TOME E8.5b uses
`P2-01A.<barcode>`. Normalize prenatal names by stripping the `run_N_` prefix and
the trailing `-N` suffix, then intersect with each training file's obs_names.
Also checks the reverse normalization for other training files.
"""

import resource

resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))

import json
import re

import anndata as ad

OUT = "/mnt/d/sc/transcriptformer/transcriptformer/.scratch"
UUIDS = [
    "04912a4e-4fad-430b-9fd7-16d30c5c57fa",
    "3776b646-d6ae-4bd1-883f-5877e328b5ff",
    "4a321ccb-ec08-42bc-808f-167bbd1127d3",
    "aaf0497e-a8a9-4a81-8b22-c1ac86507c6b",
]

pre = re.compile(r"^run_\d+_")
suf = re.compile(r"-\d+$")

norm_sets = {}
for u in UUIDS:
    with open(f"{OUT}/prenatal_obsnames/{u}.txt") as fh:
        names = fh.read().splitlines()
    norm = set(suf.sub("", pre.sub("", n)) for n in names)
    norm_sets[u] = norm
    print(f"{u[:8]}: raw={len(names)}, normalized unique={len(norm)}")
union_norm = set().union(*norm_sets.values())
print(f"union normalized: {len(union_norm)}")

manifest = json.load(open("/mnt/d/sc/transcriptformer/transcriptformer/conf/finetune_run_multispecies.json"))
mouse_files = [d["path"] for d in manifest["datasets"] if d["species"] == "mus_musculus"]
print("\nnormalized overlap vs training mus_musculus files:")
for path in mouse_files:
    label = path.split("/")[-1].replace("小鼠_Mus_musculus__", "")[:70]
    a = ad.read_h5ad(path, backed="r")
    try:
        names = list(a.obs_names)
    finally:
        a.file.close()
    s = set(names)
    inter = len(s & union_norm)
    print(f"  {label}: n={len(names)}, normalized overlap={inter} ({100*inter/max(len(s),1):.2f}%)")

# Per-big-file breakdown for E8.5b specifically
e85b_path = [p for p in mouse_files if "E8.5b" in p][0]
a = ad.read_h5ad(e85b_path, backed="r")
try:
    e85b = set(a.obs_names)
finally:
    a.file.close()
print("\nE8.5b vs each prenatal file (normalized):")
for u in UUIDS:
    print(f"  {u[:8]}: {len(e85b & norm_sets[u])}")
