"""Crash-safe local pilot cell commits; incomplete staging files are never resumed."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path
import tempfile


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class CellCheckpoints:
    def __init__(self, directory: Path, identity: dict):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.check_storage()
        self.lock = (directory / "writer.lock").open("a+b")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            normalized_identity = {key: value for key, value in identity.items() if key != "software_commit_actual"}
            self.identity = hashlib.sha256(_bytes(normalized_identity)).hexdigest()
            self.original_commit = identity["software_commit_actual"]
            path = directory / "identity.json"
            payload = _bytes({"schema": "b3_pilot_checkpoint_identity_v1", "identity": identity})
            if path.exists():
                if path.stat().st_size > 16 * 1024**2:
                    raise ValueError("Checkpoint identity exceeds bounded metadata size")
                metadata = json.loads(path.read_text())
                if metadata.get("schema") != "b3_pilot_checkpoint_identity_v1" or not isinstance(
                    metadata.get("identity"), dict
                ):
                    raise ValueError("Checkpoint identity schema differs")
                recorded = metadata["identity"]
                normalized_recorded = {key: value for key, value in recorded.items() if key != "software_commit_actual"}
                if normalized_recorded != normalized_identity:
                    raise ValueError("Checkpoint provenance differs; use a fresh checkpoint directory")
                self.original_commit = recorded["software_commit_actual"]
            else:
                self._publish(path, payload)
            history = directory / f"execution-commit-{identity['software_commit_actual']}.json"
            if not history.exists():
                self._publish(
                    history,
                    _bytes(
                        {
                            "original_commit": self.original_commit,
                            "execution_commit": identity["software_commit_actual"],
                            "identity_sha256": self.identity,
                        }
                    ),
                )
        except BaseException:
            self.lock.close()
            raise

    def check_storage(self):
        if shutil.disk_usage(self.directory).free < 2 * 1024**3:
            raise RuntimeError("Checkpoint filesystem has less than 2 GiB free")

    def _publish(self, target, payload):
        self.check_storage()
        descriptor, name = tempfile.mkstemp(prefix=".incomplete-", dir=self.directory)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    def load(self, cell_index):
        path = self.directory / f"cell-{cell_index:06d}.json"
        if not path.exists():
            return None
        if path.stat().st_size > 16 * 1024**2:
            raise ValueError("Cell checkpoint exceeds bounded metadata size")
        record = json.loads(path.read_text())
        payload = record["payload"]
        if record["sha256"] != hashlib.sha256(_bytes(payload)).hexdigest():
            raise ValueError("Cell checkpoint checksum mismatch")
        if payload["identity_sha256"] != self.identity or payload["cell_index"] != cell_index:
            raise ValueError("Cell checkpoint identity mismatch")
        return payload

    def save(self, cell_index, proof, rows):
        payload = {"identity_sha256": self.identity, "cell_index": cell_index, "proof": proof, "rows": rows}
        record = {"payload": payload, "sha256": hashlib.sha256(_bytes(payload)).hexdigest()}
        self._publish(self.directory / f"cell-{cell_index:06d}.json", _bytes(record))

    def close(self):
        self.lock.close()
