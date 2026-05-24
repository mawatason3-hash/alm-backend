import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def upload_image(file_bytes: bytes, folder: str) -> str:
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=f"alm/{folder}",
        resource_type="image",
        transformation=[
            {"width": 400, "height": 400, 
             "crop": "fill", "gravity": "face"}
        ]
    )
    return result["secure_url"]

async def delete_image(public_id: str) -> None:
    cloudinary.uploader.destroy(public_id)
