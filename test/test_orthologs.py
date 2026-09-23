"""Regression tests for the ortholog table builder (offline, synthetic fixtures).

Covers the frozen rules of docs/perturbation-and-baseline-design.md section 6: one-to-one
retention, many-to-one/many-to-many dropping, version-stripping rules, the urchin bridge
logic, coverage-floor flagging, and cross-check disagreement dropping. No network access.
"""

import gzip

import pytest

from scripts.build_ortholog_table import (
    Species,
    alliance_called_pairs,
    alliance_resolve,
    alliance_verdict,
    canonical_gene_id,
    chain_bridge,
    collect_pair_rows,
    evaluate_floors,
    filter_pair_rows,
    gene_aliases,
    iter_homology_rows,
    load_echinobase_consensus,
    match_alliance_hits,
    match_wanted,
    merge_bridge,
    orthodb_resolve,
    orthodb_verdict,
    pair_crosscheck,
    plan_pair,
    protein_coding_genes,
    select_one2one,
    strip_version_suffix,
    write_table,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ENSG00000123456.4", "ENSG00000123456"),  # human Ensembl, versioned -> stripped
        ("ENSDARG00000000001.4", "ENSDARG00000000001"),  # zebrafish Ensembl, versioned -> stripped
        ("ENSMUSG00000000001.12", "ENSMUSG00000000001"),
        ("ENSGALG00000000001.2", "ENSGALG00000000001"),
        ("ENSOCUG00000000001.5", "ENSOCUG00000000001"),
        ("WBGene00000001.1", "WBGene00000001"),  # WormBase gene ID, versioned -> stripped
        ("FBgn0000001.2", "FBgn0000001"),  # FlyBase gene ID, versioned -> stripped
        ("2L52.1", "2L52.1"),  # WormBase sequence name: the dot is part of the ID
        ("AC3.12", "AC3.12"),
        ("acy3.1", "acy3.1"),  # zebrafish paralog symbol: the dot is part of the ID
        ("LOC12345.1", "LOC12345.1"),  # not a stable database ID -> untouched
        ("GeneID_123456", "GeneID_123456"),
    ],
)
def test_version_stripping_only_stable_database_ids(raw, expected):
    assert strip_version_suffix(raw) == expected


def test_urchin_loc_and_geneid_are_one_identity():
    assert canonical_gene_id("lytechinus_variegatus", "LOC121405632") == "GeneID_121405632"
    assert canonical_gene_id("lytechinus_variegatus", "GeneID_121405632") == "GeneID_121405632"
    assert gene_aliases("lytechinus_variegatus", "LOC121405632") == ["GeneID_121405632", "LOC121405632"]
    # aliasing is urchin-only: human LOC-looking strings stay as they are
    assert canonical_gene_id("homo_sapiens", "LOC123") == "LOC123"


def test_select_one2one_retains_only_one2one_high_confidence():
    rows = [
        ("A", "B", "ortholog_one2one", "1"),
        ("A2", "B2", "ortholog_one2one", "0"),  # low orthology confidence -> dropped
        ("A3", "B3", "ortholog_one2many", "1"),  # one-to-many -> dropped
        ("A4", "B4", "ortholog_many2many", "1"),  # many-to-many -> dropped
    ]
    kept, stats = select_one2one(rows)
    assert kept == [("A", "B")]
    assert stats["n_rows"] == 4
    assert stats["n_dropped_type"] == 2
    assert stats["n_dropped_confidence"] == 1
    assert stats["n_kept_bijection"] == 1


def test_select_one2one_drops_many_to_one_without_collapsing():
    # A is one-to-many to two B genes: every row goes, A is never "collapsed" onto one B.
    rows = [
        ("A", "B1", "ortholog_one2many", "1"),
        ("A", "B2", "ortholog_one2many", "1"),
        ("C", "D", "ortholog_one2one", "1"),
    ]
    kept, _ = select_one2one(rows)
    assert kept == [("C", "D")]
    # two distinct homologies inconsistently labelled one2one still violate the bijection.
    rows = [
        ("A", "B1", "ortholog_one2one", "1"),
        ("A", "B2", "ortholog_one2one", "1"),
        ("A2", "B1", "ortholog_one2one", "1"),
    ]
    kept, stats = select_one2one(rows)
    assert kept == []
    assert stats["n_dropped_bijection"] == 3


def test_select_one2one_version_collapses_duplicates_but_not_partners():
    # same gene (two versions) to the same partner: collapses to one pair
    kept, _ = select_one2one(
        [("ENSG000001.1", "B", "ortholog_one2one", "1"), ("ENSG000001.2", "B", "ortholog_one2one", "1")]
    )
    assert kept == [("ENSG000001", "B")]
    # same gene (two versions) to two partners: ambiguous, dropped entirely
    kept, stats = select_one2one(
        [("ENSG000001.1", "B1", "ortholog_one2one", "1"), ("ENSG000001.2", "B2", "ortholog_one2one", "1")]
    )
    assert kept == []
    assert stats["n_dropped_bijection"] == 2
    # dotted non-stable IDs never merge (and two distinct genes to one partner is many-to-one)
    kept, _ = select_one2one([("2L52.1", "B1", "ortholog_one2one", "1"), ("2L52", "B2", "ortholog_one2one", "1")])
    assert kept == [("2L52", "B2"), ("2L52.1", "B1")]
    kept, stats = select_one2one([("2L52.1", "B", "ortholog_one2one", "1"), ("2L52", "B", "ortholog_one2one", "1")])
    assert kept == [] and stats["n_dropped_bijection"] == 2


def test_chain_bridge_composes_strict_one_to_one_links():
    link_lv_sp = [("lv1", "sp1"), ("lv2", "sp2"), ("lv3", "sp3"), ("lv4", "sp4")]
    link_sp_x = [("sp1", "x1"), ("sp2", "x2"), ("sp3", "x3"), ("sp3", "x3b"), ("spX", "x9")]
    bridged = chain_bridge(link_lv_sp, link_sp_x)
    # sp3 maps to two x genes -> ambiguous, dropped; sp4 has no x; spX has no lv.
    assert bridged == [("lv1", "x1"), ("lv2", "x2")]
    # a sp gene with two lv partners is dropped too
    assert chain_bridge([("lvA", "sp1"), ("lvB", "sp1")], [("sp1", "x1")]) == []


def test_merge_bridge_only_when_direct_is_thin():
    direct = [("lv1", "x1")]
    bridged = [("lv1", "x1"), ("lv2", "x2")]
    merged, used = merge_bridge(direct, bridged, threshold=5000)
    assert used and sorted(merged) == [("lv1", "x1"), ("lv2", "x2")]
    fat = [(f"lv{i}", f"x{i}") for i in range(5000)]
    merged, used = merge_bridge(fat, bridged, threshold=5000)
    assert not used and merged == sorted(fat)
    # thin but nothing to bridge with: fallback triggered only if it contributes pairs
    merged, used = merge_bridge(direct, [], threshold=5000)
    assert not used and merged == direct


def test_evaluate_floors_flagging():
    ok = evaluate_floors(8000, 10000, 10000)
    assert ok["floors_pass"] and not ok["no_data"]
    assert ok["coverage_a"] == pytest.approx(0.8)
    frac_fail = evaluate_floors(8000, 20000, 10000)  # 0.4 on side a -> floor (a) fails
    assert not frac_fail["pass_fraction_floor"] and frac_fail["pass_min_pairs_floor"]
    size_fail = evaluate_floors(4000, 5000, 5000)  # floor (b) fails
    assert size_fail["pass_fraction_floor"] and not size_fail["pass_min_pairs_floor"]
    assert not size_fail["floors_pass"]
    none = evaluate_floors(0, 10000, 10000)
    assert none["no_data"] and not none["floors_pass"]
    assert not evaluate_floors(8000, 0, 0)["floors_pass"]


def _odb_res(gene, organism):
    return {"odb_gene": gene, "organism": organism, "query": gene}


def test_orthodb_verdict_one_gene_per_species():
    a, b = _odb_res("9606_1:aaa", "9606_1"), _odb_res("10090_0:bbb", "10090_0")
    concordant = {
        "data": [
            {"gene": {"param": "9606_1:aaa"}, "clade_id": 33208, "taxon_id": "9606_1"},
            {"gene": {"param": "10090_0:bbb"}, "clade_id": 33208, "taxon_id": "10090_0"},
        ]
    }
    assert orthodb_verdict(a, b, concordant)["verdict"] == "concordant"
    # side a has two genes at every shared level -> the pairing is not one gene per species
    duplicated = {
        "data": [
            {"gene": {"param": "9606_1:aaa"}, "clade_id": 33208, "taxon_id": "9606_1"},
            {"gene": {"param": "9606_1:aaa2"}, "clade_id": 33208, "taxon_id": "9606_1"},
            {"gene": {"param": "10090_0:bbb"}, "clade_id": 33208, "taxon_id": "10090_0"},
        ]
    }
    assert orthodb_verdict(a, b, duplicated)["verdict"] == "discordant"
    assert orthodb_verdict(a, b, {"data": []})["verdict"] == "discordant"
    # an unresolved gene can never be a disagreement
    assert orthodb_verdict(a, None, concordant)["verdict"] == "unavailable"


def test_orthodb_resolve_requires_unique_match():
    class Fake:
        def genesearch(self, query):
            return self.responses.get(query, {})

    fake = Fake()
    fake.responses = {
        "ENSG1": {
            "gene": {"gene_id": {"param": "9606_1:aaa"}},
            "organism": {"id": "9606_1"},
            "nb_genes_matched_the_query": "1",
        },
        # ambiguous: two genes matched -> unresolved
        "LOC123": {
            "gene": {"gene_id": {"param": "7654_0:ccc"}},
            "organism": {"id": "7654_0"},
            "nb_genes_matched_the_query": 2,
        },
    }
    assert orthodb_resolve(fake, "homo_sapiens", "ENSG1") == {
        "odb_gene": "9606_1:aaa",
        "organism": "9606_1",
        "query": "ENSG1",
    }
    assert orthodb_resolve(fake, "lytechinus_variegatus", "LOC123") is None
    # urchin lookup falls back to the GeneID_ spelling
    fake.responses["GeneID_123"] = {
        "gene": {"gene_id": {"param": "7654_0:ccc"}},
        "organism": {"id": "7654_0"},
        "nb_genes_matched_the_query": "1",
    }
    assert orthodb_resolve(fake, "lytechinus_variegatus", "LOC123")["odb_gene"] == "7654_0:ccc"


def test_match_alliance_hits_is_exact_not_fuzzy():
    results = [
        {"curie": "HGNC:1101", "id": "HGNC:1101", "crossReferences": ["ENSEMBL:ENSG00000139618"]},
        {"curie": "HGNC:9999", "id": "HGNC:9999", "crossReferences": [{"referencedCurie": "ENSEMBL:ENSG00000139618X"}]},
    ]
    assert match_alliance_hits("ENSG00000139618", results) == "HGNC:1101"
    assert match_alliance_hits("ENSG00000139618X", results) == "HGNC:9999"
    # substring / fuzzy search noise does not resolve, and a bare CURIE local part does
    assert match_alliance_hits("ENSG0000013961", results) is None
    assert (
        match_alliance_hits("WBGene1", [{"curie": "WB:WBGene1", "id": "WB:WBGene1", "crossReferences": []}])
        == "WB:WBGene1"
    )
    # two exact hits -> ambiguous
    assert (
        match_alliance_hits(
            "ENSG1",
            [
                {"curie": "A:1", "crossReferences": ["ENSEMBL:ENSG1"]},
                {"curie": "B:1", "crossReferences": ["ENSEMBL:ENSG1"]},
            ],
        )
        is None
    )


def test_alliance_verdict_call_disagreement_and_unavailability():
    a, b = {"curie": "HGNC:1", "query": "g1"}, {"curie": "MGI:2", "query": "g2"}
    called = {
        "results": [
            {
                "geneToGeneOrthologyGenerated": {
                    "subjectGene": {"primaryExternalId": "HGNC:1"},
                    "objectGene": {"primaryExternalId": "MGI:2"},
                }
            }
        ]
    }
    assert alliance_verdict(a, b, called, {})["verdict"] == "concordant"
    other = {
        "results": [
            {
                "geneToGeneOrthologyGenerated": {
                    "subjectGene": {"primaryExternalId": "HGNC:1"},
                    "objectGene": {"primaryExternalId": "MGI:3"},
                }
            }
        ]
    }
    assert alliance_verdict(a, b, other, {})["verdict"] == "discordant"
    assert alliance_verdict(a, b, {"results": []}, {"results": []})["verdict"] == "unavailable"
    assert alliance_verdict(a, None, called, {})["verdict"] == "unavailable"
    assert alliance_called_pairs(called) == {("HGNC:1", "MGI:2")}


def test_alliance_resolve_uses_exact_hits():
    class Fake:
        def search(self, query):
            return {"results": [{"curie": "WB:WBGene1", "id": "WB:WBGene1", "crossReferences": []}]}

    assert alliance_resolve(Fake(), "caenorhabditis_elegans", "WBGene1") == {"curie": "WB:WBGene1", "query": "WBGene1"}


class FakeODB:
    def __init__(self, genes=None, orthologs=None):
        self.genes = genes or {}
        self.orthologs_response = orthologs or {"data": []}

    def genesearch(self, query):
        return self.genes.get(query, {})

    def orthologs(self, gene_id, organisms):
        return self.orthologs_response


class FakeAGR:
    def __init__(self, hits=None, orthologs=None):
        self.hits = hits or {}
        self.orthologs_response = orthologs or {"results": []}

    def search(self, query):
        return {"results": self.hits.get(query, [])}

    def orthologs(self, curie):
        return self.orthologs_response


def test_pair_crosscheck_drops_on_disagreement_keeps_unverified():
    row = {"species_a": "homo_sapiens", "gene_a": "ENSG1", "species_b": "mus_musculus", "gene_b": "ENSMUSG1"}
    resolved = {
        "ENSG1": {
            "gene": {"gene_id": {"param": "9606_1:aaa"}},
            "organism": {"id": "9606_1"},
            "nb_genes_matched_the_query": "1",
        },
        "ENSMUSG1": {
            "gene": {"gene_id": {"param": "10090_0:bbb"}},
            "organism": {"id": "10090_0"},
            "nb_genes_matched_the_query": "1",
        },
    }
    concordant = {
        "data": [
            {"gene": {"param": "9606_1:aaa"}, "clade_id": 33208, "taxon_id": "9606_1"},
            {"gene": {"param": "10090_0:bbb"}, "clade_id": 33208, "taxon_id": "10090_0"},
        ]
    }
    # OrthoDB concordant + Alliance not in scope -> keep
    out = pair_crosscheck(row, FakeODB(resolved, concordant), FakeAGR(), alliance_scope=False)
    assert out["orthodb"]["verdict"] == "concordant" and not out["drop"]
    assert out["alliance"]["verdict"] == "skipped"

    # Alliance disagrees (calls exist but not for this pair) -> drop
    agr_hits = {
        "ENSG1": [{"curie": "HGNC:1", "id": "HGNC:1", "crossReferences": ["ENSEMBL:ENSG1"]}],
        "ENSMUSG1": [{"curie": "MGI:2", "id": "MGI:2", "crossReferences": ["ENSEMBL:ENSMUSG1"]}],
    }
    other_call = {
        "results": [
            {
                "geneToGeneOrthologyGenerated": {
                    "subjectGene": {"primaryExternalId": "HGNC:1"},
                    "objectGene": {"primaryExternalId": "MGI:3"},
                }
            }
        ]
    }
    out = pair_crosscheck(row, FakeODB(resolved, concordant), FakeAGR(agr_hits, other_call), alliance_scope=True)
    assert out["alliance"]["verdict"] == "discordant" and out["drop"]

    # OrthoDB disagreement drops too; unverified sources never drop
    disagreeing = {"data": [{"gene": {"param": "9606_1:aaa"}, "clade_id": 33208, "taxon_id": "9606_1"}]}
    out = pair_crosscheck(row, FakeODB(resolved, disagreeing), FakeAGR(), alliance_scope=False)
    assert out["orthodb"]["verdict"] == "discordant" and out["drop"]
    out = pair_crosscheck(row, FakeODB({}, {}), FakeAGR(), alliance_scope=True)
    assert out["orthodb"]["verdict"] == "unavailable" and not out["drop"]


def test_plan_pair_sources_and_gaps():
    hs = Species("homo_sapiens", "9606", ("homo_sapiens", ""), True)
    mm = Species("mus_musculus", "10090", ("mus_musculus", ""), True)
    lv = Species("lytechinus_variegatus", "7665", ("", "lytechinus_variegatus_gca018143015v1"), True)
    dm = Species("drosophila_melanogaster", "7227", ("drosophila_melanogaster", "drosophila_melanogaster"), True)
    ce = Species("caenorhabditis_elegans", "6239", ("caenorhabditis_elegans", "caenorhabditis_elegans"), True)
    bf = Species("branchiostoma_floridae", "7739", ("", ""), False)
    ci = Species("ciona_intestinalis", "7719", ("ciona_intestinalis", ""), False)

    plan = plan_pair(hs, mm)
    assert plan.status == "compara" and plan.collection == "main"
    lv_dm = plan_pair(lv, dm)
    assert lv_dm.status == "compara" and lv_dm.collection == "metazoa"
    # dmel x worm is served by both collections; the Ensembl collection is preferred
    assert plan_pair(dm, ce).collection == "main"
    # urchin x vertebrate spans the two Compara collections: no homology data
    gap = plan_pair(lv, hs)
    assert gap.status == "no_homology_data"
    # amphioxus has no Compara gene set at all
    assert plan_pair(bf, hs).status == "no_compara_gene_set"
    # ciona is served against human even though it is a probe species
    assert plan_pair(ci, hs).status == "compara"


def test_match_wanted_handles_assembly_suffixes():
    wanted = ["lytechinus_variegatus", "homo_sapiens", "caenorhabditis_elegans"]
    assert match_wanted("homo_sapiens", wanted) == "homo_sapiens"
    assert match_wanted("lytechinus_variegatus_gca018143015v1", wanted) == "lytechinus_variegatus"
    assert match_wanted("priapulus_caudatus_gca000485595v2", wanted) is None


def test_homology_rows_parse_and_collect():
    header = "\t".join(
        [
            "gene_stable_id",
            "protein_stable_id",
            "species",
            "identity",
            "homology_type",
            "homology_gene_stable_id",
            "homology_protein_stable_id",
            "homology_species",
            "homology_identity",
            "dn",
            "ds",
            "goc_score",
            "wga_coverage",
            "is_high_confidence",
            "homology_id",
        ]
    )

    def row(g1, s1, g2, s2, otype, conf):
        return "\t".join([g1, "p1", s1, "50", otype, g2, "p2", s2, "50", "NULL", "NULL", "NULL", "NULL", conf, "1"])

    lines = [
        header,
        row(
            "LOC1", "lytechinus_variegatus_gca018143015v1", "WBGene2", "caenorhabditis_elegans", "ortholog_one2one", "1"
        ),
        row(
            "LOC3", "lytechinus_variegatus_gca018143015v1", "WBGene4", "caenorhabditis_elegans", "ortholog_one2one", "0"
        ),
        row("ENSG5", "homo_sapiens", "WBGene6", "caenorhabditis_elegans", "ortholog_one2one", "1"),
        row(
            "LOC7",
            "lytechinus_variegatus_gca018143015v1",
            "PPP8",
            "priapulus_caudatus_gca000485595v2",
            "ortholog_one2one",
            "1",
        ),
        row(
            "LOC9",
            "lytechinus_variegatus_gca018143015v1",
            "LOC9b",
            "lytechinus_variegatus_gca018143015v1",
            "ortholog_one2one",
            "1",
        ),
    ]
    order = {n: i for i, n in enumerate(["homo_sapiens", "lytechinus_variegatus", "caenorhabditis_elegans"])}
    # a metazoa-source file keeps only Metazoa-collection pairs (urchin rows), not human x worm
    buckets = collect_pair_rows(iter_homology_rows(lines), "metazoa", list(order), order)
    assert set(buckets) == {("lytechinus_variegatus", "caenorhabditis_elegans")}
    # rows are oriented (lower order first) regardless of column order in the dump
    raw = buckets[("lytechinus_variegatus", "caenorhabditis_elegans")]
    assert ("LOC1", "WBGene2", "ortholog_one2one", "1") in raw
    assert ("LOC3", "WBGene4", "ortholog_one2one", "0") in raw
    # a main-source file keeps the vertebrate x worm pair instead
    buckets = collect_pair_rows(iter_homology_rows(lines), "main", list(order), order)
    assert set(buckets) == {("homo_sapiens", "caenorhabditis_elegans")}

    kept, stats = filter_pair_rows(raw, "lytechinus_variegatus", "caenorhabditis_elegans")
    assert kept == [("GeneID_1", "WBGene2")]  # confidence-0 row dropped; LOC canonicalized to GeneID_
    assert stats["n_rows"] == 2 and stats["n_kept_bijection"] == 1


def test_load_echinobase_consensus_keeps_three_tool_agreement(tmp_path):
    path = tmp_path / "5ToolsLvarSpurp.tsv"
    path.write_text(
        "LVAR\tSPURP\tFO\tIP\tOF\tPO\tSO\tTOTAL\n"
        "1\t11\t1\t0\t1\t1\t1\t4\n"  # consensus >= 3 -> kept
        "2\t12\t1\t1\t0\t0\t0\t2\n"  # consensus < 3 -> dropped
        "3\t13\t1\t1\t1\t1\t1\t5\n"
        "4\t13\t1\t1\t1\t1\t1\t5\n"  # sp13 has two lv partners -> dropped as ambiguous
    )
    assert load_echinobase_consensus(path) == [("GeneID_1", "GeneID_11")]


def test_write_table_is_deterministic_tsv_gz(tmp_path):
    rows = [
        {"species_a": "homo_sapiens", "gene_a": "ENSG1", "species_b": "mus_musculus", "gene_b": "ENSMUSG1"},
        {"species_a": "homo_sapiens", "gene_a": "ENSG2", "species_b": "mus_musculus", "gene_b": "ENSMUSG2"},
    ]
    n, sha = write_table(rows, tmp_path / "t.tsv.gz")
    assert n == 2
    with gzip.open(tmp_path / "t.tsv.gz", "rt") as fh:
        assert fh.read() == (
            "homo_sapiens\tENSG1\tmus_musculus\tENSMUSG1\nhomo_sapiens\tENSG2\tmus_musculus\tENSMUSG2\n"
        )
    _, sha2 = write_table(rows, tmp_path / "t.tsv.gz")
    assert sha == sha2


def test_protein_coding_genes_counts_distinct_genes(tmp_path):
    gtf = tmp_path / "x.gtf.gz"
    with gzip.open(gtf, "wt") as fh:
        fh.write("#!genome-build test\n")
        fh.write('src\tens\tgene\t1\t10\t.\t+\t.\tgene_id "G1"; gene_biotype "protein_coding"; gene_version "2";\n')
        fh.write('src\tens\ttranscript\t1\t10\t.\t+\t.\tgene_id "G1"; gene_biotype "protein_coding";\n')
        fh.write('src\tens\tgene\t20\t30\t.\t+\t.\tgene_id "G2"; gene_biotype "lncRNA";\n')
        fh.write('src\tens\tgene\t40\t50\t.\t+\t.\tgene_id "G3"; gene_biotype "protein_coding";\n')
    assert protein_coding_genes(gtf) == {"G1", "G3"}


class BrokenODB:
    def genesearch(self, query):
        raise RuntimeError("orthodb blocked: HTTP 429 after honest throttled attempts")


class BrokenAGR:
    def search(self, query):
        raise RuntimeError("alliance blocked")


def test_service_outage_is_an_unavailable_gap_and_never_drops():
    row = {"species_a": "homo_sapiens", "gene_a": "ENSG1", "species_b": "mus_musculus", "gene_b": "ENSMUSG1"}
    out = pair_crosscheck(row, BrokenODB(), BrokenAGR(), alliance_scope=True)
    assert out["orthodb"]["verdict"] == "unavailable" and "service_unavailable" in out["orthodb"]["reason"]
    assert out["alliance"]["verdict"] == "unavailable" and "service_unavailable" in out["alliance"]["reason"]
    assert not out["drop"]
