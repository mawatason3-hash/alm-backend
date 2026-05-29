import os
import traceback
import uuid
from typing import Any, Optional, Tuple, Union

BUCKET_NAME = os.environ.get("BUCKET_NAME", "election-media")

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

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

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

    try:
        ext = _normalize_image_extension(original_filename)
        content_type = _normalize_content_type(ext)
        unique_filename = f"{folder}/{uuid.uuid4()}.{ext}"

        supabase.storage.from_(BUCKET_NAME).upload(
            unique_filename,
            file_bytes,
            {"content-type": content_type}
        )

        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(
            unique_filename
        )
        public_url = _extract_public_url(public_url)
        if not public_url:
            print(f"Supabase upload succeeded but returned no URL for {unique_filename}")
        return public_url
    except Exception:
        traceback.print_exc()
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
