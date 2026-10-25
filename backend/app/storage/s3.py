from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
import urllib.parse
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.storage.base import StorageNamespace


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = _hmac_sha256(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    return _hmac_sha256(k_service, "aws4_request")


def _uri_encode(value: str, encode_slash: bool = True) -> str:
    safe = "-_.~" if encode_slash else "-_.~/"
    return urllib.parse.quote(value, safe=safe)


class S3StorageProvider:
    """Zero-bloat S3-compatible object storage adapter using AWS Signature V4 over httpx.

    Compatible with Hetzner EU Object Storage, Cloudflare R2, Scaleway Object Storage,
    MinIO, and AWS S3 private buckets.
    """

    provider_name = "s3"

    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        key_prefix: str = "",
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.region = region.strip() or "eu-central-1"
        self.bucket = bucket.strip()
        self.access_key_id = access_key_id.strip()
        self.secret_access_key = secret_access_key.strip()
        cleaned_prefix = key_prefix.strip("/")
        self.key_prefix = f"{cleaned_prefix}/" if cleaned_prefix else ""
        self._client = http_client or httpx.Client(timeout=timeout_seconds)

        parsed = urllib.parse.urlsplit(self.endpoint_url)
        self._scheme = parsed.scheme or "https"
        self._host = parsed.netloc
        self._base_path = parsed.path.rstrip("/")

    def _parse_ref(self, storage_ref: str) -> tuple[str, str] | None:
        if not storage_ref.startswith("s3://"):
            return None
        rest = storage_ref[5:]
        slash_idx = rest.find("/")
        if slash_idx <= 0:
            raise ValueError(f"Malformed S3 storage reference: {storage_ref}")
        return rest[:slash_idx], rest[slash_idx + 1 :]

    def _canonical_uri(self, bucket: str, key: str) -> str:
        raw_path = f"{self._base_path}/{bucket}/{key.lstrip('/')}"
        return _uri_encode(raw_path, encode_slash=False)

    def _signed_headers(
        self,
        method: str,
        canonical_uri: str,
        payload_sha256: str,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        headers: dict[str, str] = {
            "host": self._host,
            "x-amz-content-sha256": payload_sha256,
            "x-amz-date": amz_date,
        }
        if extra_headers:
            for k, v in extra_headers.items():
                headers[k.lower()] = v.strip()

        sorted_keys = sorted(headers.keys())
        canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted_keys)
        signed_headers_str = ";".join(sorted_keys)

        canonical_request = "\n".join(
            [
                method.upper(),
                canonical_uri,
                "",
                canonical_headers,
                signed_headers_str,
                payload_sha256,
            ]
        )
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        sig_key = _signing_key(self.secret_access_key, date_stamp, self.region, "s3")
        signature = hmac.new(
            sig_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        out_headers = dict(headers)
        out_headers["Authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, Signature={signature}"
        )
        return out_headers

    def save_file(
        self,
        namespace: StorageNamespace,
        filename: str,
        source_path: Path,
        content_type: str = "application/pdf",
    ) -> str:
        safe_name = os.path.basename(filename)
        if not safe_name or safe_name in (".", ".."):
            raise ValueError("Invalid storage filename.")
        key = f"{self.key_prefix}{namespace}/{safe_name}"
        payload = source_path.read_bytes()
        payload_hash = hashlib.sha256(payload).hexdigest()
        canonical_uri = self._canonical_uri(self.bucket, key)
        headers = self._signed_headers(
            "PUT",
            canonical_uri,
            payload_hash,
            extra_headers={"content-type": content_type},
        )
        url = f"{self._scheme}://{self._host}{canonical_uri}"
        resp = self._client.put(url, content=payload, headers=headers)
        if resp.status_code not in (200, 201, 204):
            raise OSError(f"S3 upload failed with HTTP {resp.status_code}.")
        return f"s3://{self.bucket}/{key}"

    def exists(self, storage_ref: str) -> bool:
        if not storage_ref:
            return False
        parsed = self._parse_ref(storage_ref)
        if parsed is None:
            return Path(storage_ref).is_file()
        bucket, key = parsed
        canonical_uri = self._canonical_uri(bucket, key)
        empty_hash = hashlib.sha256(b"").hexdigest()
        headers = self._signed_headers("HEAD", canonical_uri, empty_hash)
        url = f"{self._scheme}://{self._host}{canonical_uri}"
        resp = self._client.head(url, headers=headers)
        return resp.status_code == 200

    def get_bytes(self, storage_ref: str) -> bytes:
        parsed = self._parse_ref(storage_ref)
        if parsed is None:
            p = Path(storage_ref)
            if not p.is_file():
                raise FileNotFoundError(f"Stored file not found: {storage_ref}")
            return p.read_bytes()
        bucket, key = parsed
        canonical_uri = self._canonical_uri(bucket, key)
        empty_hash = hashlib.sha256(b"").hexdigest()
        headers = self._signed_headers("GET", canonical_uri, empty_hash)
        url = f"{self._scheme}://{self._host}{canonical_uri}"
        resp = self._client.get(url, headers=headers)
        if resp.status_code == 404:
            raise FileNotFoundError(f"S3 object not found: {storage_ref}")
        if resp.status_code != 200:
            raise OSError(f"S3 download failed with HTTP {resp.status_code}.")
        return bytes(resp.content)

    @contextmanager
    def local_path(self, storage_ref: str) -> Iterator[Path]:
        parsed = self._parse_ref(storage_ref)
        if parsed is None:
            p = Path(storage_ref)
            if not p.is_file():
                raise FileNotFoundError(f"Stored file not found: {storage_ref}")
            yield p
            return

        payload = self.get_bytes(storage_ref)
        suffix = Path(parsed[1]).suffix or ".pdf"
        fd, tmp_name = tempfile.mkstemp(prefix="afa-s3-", suffix=suffix)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
            yield tmp_path
        finally:
            tmp_path.unlink(missing_ok=True)

    def delete(self, storage_ref: str) -> bool:
        if not storage_ref:
            return False
        parsed = self._parse_ref(storage_ref)
        if parsed is None:
            p = Path(storage_ref)
            if p.is_file():
                try:
                    p.unlink()
                    return True
                except OSError:
                    return False
            return False

        bucket, key = parsed
        canonical_uri = self._canonical_uri(bucket, key)
        empty_hash = hashlib.sha256(b"").hexdigest()
        headers = self._signed_headers("DELETE", canonical_uri, empty_hash)
        url = f"{self._scheme}://{self._host}{canonical_uri}"
        resp = self._client.delete(url, headers=headers)
        return resp.status_code in (200, 202, 204)

    def presigned_download_url(
        self,
        storage_ref: str,
        filename: str,
        expires_in_seconds: int = 300,
    ) -> str | None:
        parsed = self._parse_ref(storage_ref)
        if parsed is None:
            return None
        bucket, key = parsed
        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        canonical_uri = self._canonical_uri(bucket, key)

        safe_disp_name = os.path.basename(filename).replace('"', "")
        query_params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key_id}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(max(1, min(expires_in_seconds, 604800))),
            "X-Amz-SignedHeaders": "host",
            "response-content-disposition": f'attachment; filename="{safe_disp_name}"',
        }
        sorted_qp = sorted(query_params.items())
        canonical_qs = "&".join(
            f"{_uri_encode(k)}={_uri_encode(v)}" for k, v in sorted_qp
        )
        canonical_headers = f"host:{self._host}\n"
        canonical_request = "\n".join(
            [
                "GET",
                canonical_uri,
                canonical_qs,
                canonical_headers,
                "host",
                "UNSIGNED-PAYLOAD",
            ]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        sig_key = _signing_key(self.secret_access_key, date_stamp, self.region, "s3")
        signature = hmac.new(
            sig_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return (
            f"{self._scheme}://{self._host}{canonical_uri}"
            f"?{canonical_qs}&X-Amz-Signature={signature}"
        )
