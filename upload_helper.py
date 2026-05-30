import os
import traceback
import uuid
from typing import Any, Optional, Tuple, Union

import httpx


def _get_env_var(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            print(f"Using env var {name} for Supabase configuration")
            return value
    return default

BUCKET_NAME = _get_env_var("BUCKET_NAME", "NEXT_PUBLIC_SUPABASE_BUCKET", default="election-media")

_supabase_client = None
_SUPABASE_AVAILABLE = False


def _normalize_image_extension(filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    if ext in ["jpg", "jpeg", "png", "webp"]:
        return ext
    return "jpg"


def _normalize_content_type(ext: str) -> str:
    return "image/jpeg" if ext in {"jpg", "jpeg"} else f"image/{ext}"


def _extract_public_url(value: Union[str, dict, None]) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "publicURL" in value:
            return value["publicURL"]
        if "publicUrl" in value:
            return value["publicUrl"]
        if "data" in value and isinstance(value["data"], dict):
            return value["data"].get("publicURL") or value["data"].get("publicUrl") or ""
    return str(value)


def _init_supabase_client() -> Tuple[Optional[object], bool]:
    global _supabase_client, _SUPABASE_AVAILABLE
    if _supabase_client is not None:
        return _supabase_client, _SUPABASE_AVAILABLE

    SUPABASE_URL = _get_env_var("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    SUPABASE_KEY = _get_env_var("SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        _supabase_client = None
        _SUPABASE_AVAILABLE = False
        print("Supabase env vars are missing; upload will be skipped")
        return None, False

    try:
        from supabase import create_client

        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        _SUPABASE_AVAILABLE = True
        return _supabase_client, True
    except Exception:
        traceback.print_exc()
        _supabase_client = None
        _SUPABASE_AVAILABLE = False
        return None, False


def upload_image(file_bytes: bytes, original_filename: str,
                 folder: str = "general") -> str:
    supabase, available = _init_supabase_client()
    if not available or supabase is None:
        return ""

    supabase_url = _get_env_var("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = _get_env_var("SUPABASE_KEY", "NEXT_PUBLIC_SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("Supabase URL or key missing; upload skipped")
        return ""

    try:
        ext = _normalize_image_extension(original_filename)
        content_type = _normalize_content_type(ext)
        unique_filename = f"{folder}/{uuid.uuid4()}.{ext}"
        upload_url = f"{supabase_url.rstrip('/')}/storage/v1/object/{BUCKET_NAME}/{unique_filename}"

        with httpx.Client(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
            response = client.post(
                upload_url,
                content=file_bytes,
                headers={
                    "Authorization": f"Bearer {supabase_key}",
                    "apikey": supabase_key,
                    "Content-Type": content_type,
                },
            )
            response.raise_for_status()

        public_url = f"{supabase_url.rstrip('/')}/storage/v1/object/public/{BUCKET_NAME}/{unique_filename}"
        return public_url
    except Exception as exc:
        traceback.print_exc()
        print(f"Upload failed: {exc}")
        return ""


def delete_image(public_url: str) -> None:
    supabase, available = _init_supabase_client()
    if not available or supabase is None:
        return

    try:
        path = public_url.split(
            f"/object/public/{BUCKET_NAME}/"
        )[-1]
        supabase.storage.from_(BUCKET_NAME).remove([path])
    except Exception:
        traceback.print_exc()
