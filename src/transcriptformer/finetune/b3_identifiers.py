"""Canonical gene identifiers used by the B3 prepared-input gate."""

import re

_VERSIONED = re.compile(r"^(ENS[A-Z]*\d+|FBgn\d+|WBGene\d+)\.\d+$")
_ALIAS = re.compile(r"^(?:LOC|GeneID_)(\d+)$")


def canonical_gene_id(species, gene_id):
    if _VERSIONED.match(gene_id):
        gene_id = gene_id.rsplit(".", 1)[0]
    if species in {"lytechinus_variegatus", "strongylocentrotus_purpuratus"}:
        match = _ALIAS.match(gene_id)
        if match:
            return f"GeneID_{match.group(1)}"
    return gene_id
