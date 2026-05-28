import os
import uuid
from supabase import create_client, Client

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://feelkkylhalqoxsgzcyv.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlZWxra3lsaGFscW94c2d6Y3l2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTk5NDk5NiwiZXhwIjoyMDk1NTcwOTk2fQ.SGyLpfatNHdu7OEK8iWI9McVSiw4-NSRURDWSCzfIEw"
)
BUCKET_NAME = "election-media"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image(file_bytes: bytes, original_filename: str,
                 folder: str = "general") -> str:
    """
    Upload image to Supabase Storage.
    Returns permanent public URL.
    folder options: 'candidates', 'voters', 'general'
    """
    ext = original_filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        ext = "jpg"
    
    unique_filename = f"{folder}/{uuid.uuid4()}.{ext}"
    
    supabase.storage.from_(BUCKET_NAME).upload(
        path=unique_filename,
        file=file_bytes,
        file_options={"content-type": f"image/{ext}"}
    )
    
    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(
        unique_filename
    )
    
    return public_url

def delete_image(public_url: str) -> None:
    """
    Delete image from Supabase Storage using its public URL.
    Call this when replacing or deleting a photo.
    """
    try:
        path = public_url.split(
            f"/object/public/{BUCKET_NAME}/"
        )[-1]
        supabase.storage.from_(BUCKET_NAME).remove([path])
    except Exception:
        pass
