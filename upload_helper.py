import mimetypes
import os
import uuid
from pathlib import Path
from fastapi import UploadFile

UPLOAD_FOLDER = os.path.join('static', 'uploads')


def _normalize_extension(filename: str, content_type: str | None) -> str:
    ext = Path(filename).suffix
    if not ext and content_type:
        ext = mimetypes.guess_extension(content_type) or ''
    if ext == '.jpe':
        ext = '.jpg'
    return ext.lower()


async def save_upload_file(upload_file: UploadFile, upload_folder: str = UPLOAD_FOLDER) -> str:
    os.makedirs(upload_folder, exist_ok=True)
    extension = _normalize_extension(upload_file.filename or '', upload_file.content_type)
    filename = f"{uuid.uuid4().hex}{extension}"
    destination_path = os.path.join(upload_folder, filename)

    content = await upload_file.read()
    with open(destination_path, 'wb') as output_file:
        output_file.write(content)

    return f"/static/uploads/{filename}"
