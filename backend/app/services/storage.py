"""GCS artifact store (fake-gcs-server locally, real GCS in prod)."""

from __future__ import annotations

import json
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, unquote

from google.cloud import storage


class ArtifactStore(Protocol):
    def upload_run(
        self,
        run_id: str,
        local_dir: Path,
        *,
        username: str,
    ) -> dict[str, dict[str, str]]: ...

    def get_run_index(self, run_id: str, *, username: str) -> dict[str, Any] | None: ...

    def download_artifact(
        self,
        *,
        username: str,
        run_id: str,
        relative_path: str,
    ) -> tuple[bytes, str]: ...


def _api_artifact_url(*, username: str, run_id: str, rel: str) -> str:
    """Same-origin API path so the browser never hits GCS directly (CORS / private bucket)."""
    return (
        f"/api/simulations/{quote(run_id, safe='')}/artifacts/"
        f"{quote(rel, safe='/')}?username={quote(username)}"
    )


def rewrite_artifact_urls(
    artifacts: dict[str, Any],
    *,
    username: str,
    run_id: str,
) -> dict[str, dict[str, str]]:
    """Normalize stored URLs (incl. legacy public GCS links) to API proxy paths."""
    marker = f"/{username}/{run_id}/"
    out: dict[str, dict[str, str]] = {"data": {}, "tables": {}, "plots": {}}
    for kind in ("data", "tables", "plots"):
        for key, url in (artifacts.get(kind) or {}).items():
            if not isinstance(url, str):
                continue
            if url.startswith("/api/simulations/"):
                out[kind][key] = url
                continue
            if marker in url:
                rel = unquote(url.split(marker, 1)[1].split("?", 1)[0])
                out[kind][key] = _api_artifact_url(
                    username=username, run_id=run_id, rel=rel
                )
            else:
                out[kind][key] = url
    return out


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
        # Only auto-create against the local emulator; prod buckets are provisioned ahead of time.
        if self.emulator_host and not bucket.exists():
            bucket = self._client.create_bucket(self.bucket_name)
        return bucket

    @staticmethod
    def _prefix(username: str, run_id: str) -> str:
        return f"{username}/{run_id}"

    @staticmethod
    def _safe_relative_path(relative_path: str) -> str:
        rel = Path(relative_path.replace("\\", "/"))
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Invalid artifact path")
        return rel.as_posix()

    def upload_run(
        self,
        run_id: str,
        local_dir: Path,
        *,
        username: str,
    ) -> dict[str, dict[str, str]]:
        local_dir = Path(local_dir)
        if not local_dir.is_dir():
            raise FileNotFoundError(f"Run directory not found: {local_dir}")

        prefix = self._prefix(username, run_id)
        files = [p for p in sorted(local_dir.rglob("*")) if p.is_file()]

        def _upload_one(path: Path) -> tuple[str, str]:
            rel = path.relative_to(local_dir).as_posix()
            blob_name = f"{prefix}/{rel}"
            blob = self._bucket.blob(blob_name)
            blob.upload_from_filename(str(path))
            url = _api_artifact_url(username=username, run_id=run_id, rel=rel)
            return rel, url

        urls: dict[str, dict[str, str]] = {"data": {}, "tables": {}, "plots": {}}
        workers = min(8, max(1, len(files)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_upload_one, path) for path in files]
            for fut in as_completed(futures):
                rel, url = fut.result()
                self._classify_and_store(urls, rel, url)

        index = {
            "run_id": run_id,
            "username": username,
            "artifacts": urls,
        }
        index_blob = self._bucket.blob(f"{prefix}/artifact_index.json")
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

    def get_run_index(self, run_id: str, *, username: str) -> dict[str, Any] | None:
        blob = self._bucket.blob(f"{self._prefix(username, run_id)}/artifact_index.json")
        if not blob.exists():
            return None
        index = json.loads(blob.download_as_text())
        artifacts = index.get("artifacts") or {}
        index["artifacts"] = rewrite_artifact_urls(
            artifacts, username=username, run_id=run_id
        )
        return index

    def download_artifact(
        self,
        *,
        username: str,
        run_id: str,
        relative_path: str,
    ) -> tuple[bytes, str]:
        rel = self._safe_relative_path(relative_path)
        blob = self._bucket.blob(f"{self._prefix(username, run_id)}/{rel}")
        if not blob.exists():
            raise FileNotFoundError(rel)
        data = blob.download_as_bytes()
        content_type = blob.content_type or mimetypes.guess_type(rel)[0] or "application/octet-stream"
        return data, content_type

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
