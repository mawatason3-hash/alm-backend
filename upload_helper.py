import os
import uuid
from typing import Optional, Tuple

# Do NOT store secrets in source. Rely on environment variables set in
# Railway / Vercel. If missing, `get_supabase()` will raise a clear error.
BUCKET_NAME = os.environ.get("BUCKET_NAME", "election-media")

# Lazy-initialized supabase client and availability flag
_supabase_client = None
_SUPABASE_AVAILABLE = False


def get_supabase() -> Tuple[Optional[object], bool]:
    """Lazily create and return (supabase_client, available).

    Raises RuntimeError if required env vars are missing or initialization fails.
    """
    global _supabase_client, _SUPABASE_AVAILABLE
    if _supabase_client is not None:
        return _supabase_client, _SUPABASE_AVAILABLE

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        _supabase_client = None
        _SUPABASE_AVAILABLE = False
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables are required for uploads.")

    try:
        # Import inside function to avoid import-time failures in environments
        # that do not have the supabase package installed (e.g., some editor tooling).
        from supabase import create_client

        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        _SUPABASE_AVAILABLE = True
        return _supabase_client, _SUPABASE_AVAILABLE
    except Exception as e:
        _supabase_client = None
        _SUPABASE_AVAILABLE = False
        raise RuntimeError(f"Failed to initialize Supabase client: {e}")


def upload_image(file_bytes: bytes, original_filename: str,
                 folder: str = "general") -> str:
    try:
        supabase, available = get_supabase()
    except RuntimeError as e:
        # Fail fast with a clear message; in production envs these vars should exist.
        print(f"Supabase unavailable: {e}")
        return ""

    if not available or supabase is None:
        print("Supabase not available, skipping upload")
        return ""

    try:
        ext = original_filename.split(".")[-1].lower()
        if ext not in ["jpg", "jpeg", "png", "webp"]:
            ext = "jpg"
        unique_filename = f"{folder}/{uuid.uuid4()}.{ext}"

        # Legacy (v1.x) supabase client upload syntax
        supabase.storage.from_(BUCKET_NAME).upload(
            unique_filename,
            file_bytes,
            {"content-type": f"image/{ext}"}
        )

        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(
            unique_filename
        )
        return public_url
    except Exception as e:
        print(f"Upload failed: {e}")
        return ""


def delete_image(public_url: str) -> None:
    try:
        supabase, available = get_supabase()
    except RuntimeError:
        return

    if not available or supabase is None:
        return

    try:
        path = public_url.split(
            f"/object/public/{BUCKET_NAME}/"
        )[-1]
        supabase.storage.from_(BUCKET_NAME).remove([path])
    except Exception as e:
        print(f"Delete failed: {e}")
