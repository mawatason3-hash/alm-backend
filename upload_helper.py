import os
import traceback
import uuid
from typing import Optional

from supabase import create_client

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://feelkkylhalqoxsgzcyv.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlZWxra3lsaGFscW94c2d6Y3l2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTk5NDk5NiwiZXhwIjoyMDk1NTcwOTk2fQ.SGyLpfatNHdu7OEK8iWI9McVSiw4-NSRURDWSCzfIEw"
)
BUCKET_NAME = "election-media"

# Supabase bucket "election-media" must be set to PUBLIC in Supabase dashboard → Storage → election-media
# → Bucket settings → Public bucket: ON

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_AVAILABLE = True
    print("✅ Supabase connected")
except Exception as e:
    print(f"❌ Supabase failed: {e}")
    traceback.print_exc()
    supabase = None
    SUPABASE_AVAILABLE = False


def _normalize_image_extension(filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    if ext in ["jpg", "jpeg", "png", "webp"]:
        return ext
    return "jpg"


def upload_image(file_bytes: bytes, original_filename: str, folder: str = "general") -> str:
    if not SUPABASE_AVAILABLE or not supabase:
        print("Supabase not available")
        return ""

    try:
        ext = _normalize_image_extension(original_filename)
        path = f"{folder}/{uuid.uuid4()}.{ext}"

        res = supabase.storage.from_(BUCKET_NAME).upload(
            path,
            file_bytes,
            {"content-type": f"image/{ext}", "x-upsert": "true"}
        )
        print(f"Upload result: {res}")

        url_res = supabase.storage.from_(BUCKET_NAME).get_public_url(path)
        print(f"Public URL: {url_res}")

        if isinstance(url_res, str):
            return url_res
        if isinstance(url_res, dict):
            return url_res.get("publicURL") or url_res.get("publicUrl") or url_res.get("data", {}).get("publicUrl", "")
        return ""
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        traceback.print_exc()
        return ""


def delete_image(public_url: str) -> None:
    if not SUPABASE_AVAILABLE or not supabase:
        return

    try:
        path = public_url.split(f"/object/public/{BUCKET_NAME}/")[-1]
        supabase.storage.from_(BUCKET_NAME).remove([path])
    except Exception:
        traceback.print_exc()
