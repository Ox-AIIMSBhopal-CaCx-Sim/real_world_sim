"""GCS artifact store (fake-gcs-server locally, real GCS in prod)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from google.cloud import storage


class ArtifactStore(Protocol):
    def upload_run(self, run_id: str, local_dir: Path) -> dict[str, dict[str, str]]: ...

    def get_run_index(self, run_id: str) -> dict[str, Any] | None: ...


def _public_object_url(
    *,
    bucket: str,
    blob_name: str,
    emulator_host: str | None,
) -> str:
    """Build a browser-fetchable URL for an uploaded object."""
    if emulator_host:
        host = emulator_host.rstrip("/")
        # fake-gcs-server public download path
        return f"{host}/download/storage/v1/b/{bucket}/o/{quote(blob_name, safe='')}/?alt=media"
    return f"https://storage.googleapis.com/{bucket}/{quote(blob_name, safe='/')}"


class GCSArtifactStore:
    """Upload a local run folder to GCS and return nested HTTP URL maps."""

    def __init__(
        self,
        *,
        bucket_name: str | None = None,
        emulator_host: str | None = None,
        project: str | None = None,
    ) -> None:
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET", "sim-results")
        raw_host = emulator_host if emulator_host is not None else os.getenv("GCS_EMULATOR_HOST")
        self.emulator_host = raw_host.rstrip("/") if raw_host else None
        self.project = project or os.getenv("GCS_PROJECT", "local-dev")

        client_kwargs: dict[str, Any] = {"project": self.project}
        if self.emulator_host:
            # google-cloud-storage expects host:port without scheme
            host_no_scheme = self.emulator_host.replace("https://", "").replace("http://", "")
            os.environ["STORAGE_EMULATOR_HOST"] = host_no_scheme
            client_kwargs["client_options"] = {"api_endpoint": self.emulator_host}

        self._client = storage.Client(**client_kwargs)
        self._bucket = self._ensure_bucket()

    def _ensure_bucket(self) -> storage.Bucket:
        bucket = self._client.bucket(self.bucket_name)
        if not bucket.exists():
            bucket = self._client.create_bucket(self.bucket_name)
        return bucket

    def upload_run(self, run_id: str, local_dir: Path) -> dict[str, dict[str, str]]:
        local_dir = Path(local_dir)
        if not local_dir.is_dir():
            raise FileNotFoundError(f"Run directory not found: {local_dir}")

        urls: dict[str, dict[str, str]] = {"data": {}, "tables": {}, "plots": {}}

        for path in sorted(local_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(local_dir).as_posix()
            blob_name = f"{run_id}/{rel}"
            blob = self._bucket.blob(blob_name)
            blob.upload_from_filename(str(path))
            url = _public_object_url(
                bucket=self.bucket_name,
                blob_name=blob_name,
                emulator_host=self.emulator_host,
            )
            self._classify_and_store(urls, rel, url)

        index = {
            "run_id": run_id,
            "artifacts": urls,
        }
        index_blob = self._bucket.blob(f"{run_id}/artifact_index.json")
        index_blob.upload_from_string(
            json.dumps(index, indent=2),
            content_type="application/json",
        )
        # also persist locally for GET fallback without GCS roundtrip
        (local_dir / "artifact_index.json").write_text(
            json.dumps(index, indent=2) + "\n",
            encoding="utf-8",
        )
        return urls

    def get_run_index(self, run_id: str) -> dict[str, Any] | None:
        blob = self._bucket.blob(f"{run_id}/artifact_index.json")
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())

    @staticmethod
    def _classify_and_store(urls: dict[str, dict[str, str]], rel: str, url: str) -> None:
        name = Path(rel).name
        stem = Path(rel).stem

        if rel.startswith("analysis/") and name.endswith(".csv"):
            urls["tables"][stem] = url
            return
        if rel.startswith("analysis/") and name.endswith(".png"):
            # strip common suffixes for stable plot keys
            key = stem
            if key.endswith("_all"):
                key = key[: -len("_all")]
            urls["plots"][key] = url
            return

        data_names = {
            "patient_timestamps": "patient_timestamps",
            "slide_timestamps": "slide_timestamps",
            "parameters": "parameters",
            "resource_busy_intervals": "resource_busy_intervals",
            "resource_productive_intervals": "resource_productive_intervals",
            "resource_metadata": "resource_metadata",
            "run_manifest": "run_manifest",
        }
        if stem in data_names and not rel.startswith("analysis/"):
            urls["data"][data_names[stem]] = url


def get_artifact_store() -> GCSArtifactStore:
    return GCSArtifactStore()
