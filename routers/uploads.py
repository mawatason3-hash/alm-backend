from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from auth import get_current_admin
from upload_helper import upload_image

router = APIRouter()

@router.post('/image')
async def upload_image(file: UploadFile = File(...), admin=Depends(get_current_admin)):
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(400, 'Only image files are supported for upload.')

    try:
        file_bytes = await file.read()
        path = upload_image(
            file_bytes=file_bytes,
            original_filename=file.filename,
            folder='general'
        )
        return {'path': path}
    except Exception as exc:
        raise HTTPException(500, f'Failed to save upload: {exc}')
