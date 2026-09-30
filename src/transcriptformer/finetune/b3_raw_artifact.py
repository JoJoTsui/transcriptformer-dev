"""Write a bounded-memory, provenance-bearing B3 per-cell score artifact."""

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite
from os import fsync, link
from pathlib import Path
from tempfile import NamedTemporaryFile
import json

from transcriptformer.finetune.b3_cell_stream import B3CellImpact


SCHEMA = "b3_gene_id_cell_impacts_v1"
SCORE_DEFINITION = "matched_target_gene_id_context_impact_v1"
MAX_ROWS = 100_000
MAX_BYTES = 64 * 1024 * 1024
REQUIRED_METHOD_INPUTS = frozenset(
    {"preprocessing_config", "ordered_vocabulary", "phase_assignment", "embryo_assignment", "split_assignment"}
)


@dataclass(frozen=True)
class B3InputDigest:
    """A byte digest and how it was established.

    ``declared`` means supplied by the caller and is not a local verification.
    ``verified_file_bytes`` means this process read the entire local file.
    """

    identifier: str
    sha256: str
    evidence: str

    @classmethod
    def declared(cls, identifier: str, digest: str) -> "B3InputDigest":
        return cls(identifier, digest, "declared")

    @classmethod
    def from_file(cls, path: str | Path) -> "B3InputDigest":
        source = Path(path)
        digest = sha256()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return cls(str(source.resolve()), digest.hexdigest(), "verified_file_bytes")

    def validate(self) -> None:
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("B3 input identifier must be nonempty")
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            raise ValueError("B3 input SHA-256 must be 64 lowercase hex characters")
        if self.evidence not in ("declared", "verified_file_bytes"):
            raise ValueError("B3 input digest evidence must be declared or verified_file_bytes")


@dataclass(frozen=True)
class B3ArtifactProvenance:
    run_id: str
    model_arm: str
    score_definition: str
    checkpoint: B3InputDigest
    manifest: B3InputDigest
    prepared_sources: tuple[B3InputDigest, ...]
    method_inputs: Mapping[str, B3InputDigest]
    metadata: Mapping[str, str]

    def validate(self) -> None:
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.run_id, self.model_arm, self.score_definition)
        ):
            raise ValueError("B3 run ID, model arm, and score definition must be nonempty strings")
        self.checkpoint.validate()
        self.manifest.validate()
        if not self.prepared_sources:
            raise ValueError("B3 artifact requires at least one prepared source digest")
        for source in self.prepared_sources:
            source.validate()
        identifiers = [source.identifier for source in self.prepared_sources]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("B3 prepared source identifiers must be unique")
        if self.score_definition != SCORE_DEFINITION:
            raise ValueError(f"B3 score definition must be {SCORE_DEFINITION}")
        if set(self.method_inputs) != REQUIRED_METHOD_INPUTS:
            raise ValueError("B3 method inputs must include preprocessing, order, phase, embryo and split digests")
        for method_input in self.method_inputs.values():
            method_input.validate()
        software_commit = self.metadata.get("software_commit")
        if (
            not isinstance(software_commit, str)
            or len(software_commit) not in (40, 64)
            or any(character not in "0123456789abcdef" for character in software_commit)
        ):
            raise ValueError("B3 provenance requires a full lowercase hexadecimal software_commit")
        if any(
            not isinstance(key, str) or not key.strip() or not isinstance(value, str)
            for key, value in self.metadata.items()
        ):
            raise ValueError("B3 provenance metadata requires nonempty string keys and string values")
        if set(self.metadata) != {"software_commit"}:
            raise ValueError("B3 provenance metadata accepts only software_commit")


@dataclass(frozen=True)
class B3ArtifactSummary:
    path: Path
    sha256: str
    row_count: int
    scored_count: int
    no_matched_target_count: int


def _json_line(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _validate_row(row: B3CellImpact, model_arm: str) -> None:
    if not isinstance(row, B3CellImpact):
        raise TypeError("B3 artifact rows must be B3CellImpact records")
    for name in ("species", "phase", "embryo_id", "source_id", "cell_id", "model_arm", "gene_id"):
        value = getattr(row, name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"B3 row {name} must be a nonempty string")
    if row.model_arm != model_arm:
        raise ValueError("B3 row model arm differs from artifact provenance")
    if isinstance(row.token_position, bool) or not isinstance(row.token_position, int) or row.token_position < 0:
        raise ValueError("B3 row token position must be a nonnegative integer")
    if isinstance(row.n_targets, bool) or not isinstance(row.n_targets, int) or row.n_targets < 0:
        raise ValueError("B3 row target count must be a nonnegative integer")
    if row.status == "scored":
        if (
            row.n_targets == 0
            or isinstance(row.impact_bits, bool)
            or not isinstance(row.impact_bits, (int, float))
            or not isfinite(row.impact_bits)
        ):
            raise ValueError("Scored B3 row requires matched targets and a finite impact")
    elif row.status == "no_matched_target":
        if row.n_targets != 0 or row.impact_bits is not None:
            raise ValueError("Unscored B3 row requires zero targets and no impact")
    else:
        raise ValueError("Unknown B3 row status")


def write_b3_raw_artifact(
    rows: Iterable[B3CellImpact], output_path: str | Path, *, provenance: B3ArtifactProvenance
) -> B3ArtifactSummary:
    """Stream JSONL to a same-directory temporary file, then publish without overwrite.

    The header distinguishes caller-declared hashes from file-byte hashes
    verified by ``B3InputDigest.from_file``. The footer contains the SHA-256
    of all row lines; the returned digest covers the entire published file.
    Neither a model nor the complete score table is held in memory here.
    """
    provenance.validate()
    destination = Path(output_path)
    if destination.exists():
        raise FileExistsError(destination)
    row_digest = sha256()
    artifact_digest = sha256()
    counts = {"scored": 0, "no_matched_target": 0}
    row_count = 0
    byte_count = 0
    seen: set[tuple[str, ...]] = set()
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)

            def write_line(value: dict[str, object], *, score_row: bool = False) -> None:
                nonlocal byte_count
                payload = _json_line(value)
                if byte_count + len(payload) > MAX_BYTES:
                    raise ValueError(f"B3 artifact exceeds {MAX_BYTES} byte cap")
                stream.write(payload)
                byte_count += len(payload)
                artifact_digest.update(payload)
                if score_row:
                    row_digest.update(payload)

            write_line(
                {
                    "kind": "header",
                    "schema": SCHEMA,
                    "provenance": {
                        "run_id": provenance.run_id,
                        "model_arm": provenance.model_arm,
                        "score_definition": provenance.score_definition,
                        "checkpoint": asdict(provenance.checkpoint),
                        "manifest": asdict(provenance.manifest),
                        "prepared_sources": [asdict(source) for source in provenance.prepared_sources],
                        "method_inputs": {key: asdict(value) for key, value in provenance.method_inputs.items()},
                        "metadata": dict(provenance.metadata),
                    },
                }
            )
            for row in rows:
                _validate_row(row, provenance.model_arm)
                if row_count >= MAX_ROWS:
                    raise ValueError(f"B3 artifact exceeds {MAX_ROWS} row cap")
                identity = (
                    row.species,
                    row.phase,
                    row.model_arm,
                    row.embryo_id,
                    row.source_id,
                    row.cell_id,
                    row.gene_id,
                )
                if identity in seen:
                    raise ValueError("Duplicate B3 cell-gene identity")
                seen.add(identity)
                write_line({"kind": "cell_impact", **asdict(row)}, score_row=True)
                row_count += 1
                counts[row.status] += 1
            write_line(
                {
                    "kind": "footer",
                    "row_count": row_count,
                    "scored_count": counts["scored"],
                    "no_matched_target_count": counts["no_matched_target"],
                    "rows_sha256": row_digest.hexdigest(),
                }
            )
            stream.flush()
            fsync(stream.fileno())
        # Hard-link creation fails if the destination exists, including a
        # concurrent writer's destination. It never replaces an existing file.
        link(temporary, destination)
        return B3ArtifactSummary(
            destination, artifact_digest.hexdigest(), row_count, counts["scored"], counts["no_matched_target"]
        )
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
