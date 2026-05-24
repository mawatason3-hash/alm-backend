from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from auth import get_current_admin
from upload_helper import save_upload_file

router = APIRouter()

@router.post('/image')
async def upload_image(file: UploadFile = File(...), admin=Depends(get_current_admin)):
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(400, 'Only image files are supported for upload.')

    try:
        path = await save_upload_file(file)
        return {'path': path}
    except Exception as exc:
        raise HTTPException(500, f'Failed to save upload: {exc}')
