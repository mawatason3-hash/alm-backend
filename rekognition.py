import os
import base64
import requests
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from io import BytesIO
from urllib.parse import urlparse
from PIL import Image


def get_rekognition_client():
    key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

    print(f"AWS Key present: {bool(key)}")
    print(f"AWS Secret present: {bool(secret)}")
    print(f"AWS Region: {region}")

    if not key or not secret:
        raise RuntimeError("AWS credentials not configured")

    try:
        return boto3.client(
            "rekognition",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=region
        )
    except Exception as exc:
        raise RuntimeError(f"Unable to create Rekognition client: {exc}") from exc


def decode_image_base64(image_data: str) -> bytes:
    if not image_data:
        raise ValueError('Selfie image data is required.')

    if ',' in image_data:
        image_data = image_data.split(',', 1)[1]

    try:
        raw_bytes = base64.b64decode(image_data)
    except Exception as exc:
        raise ValueError('Invalid selfie image encoding.') from exc

    try:
        img = Image.open(BytesIO(raw_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        output = BytesIO()
        img.save(output, format='JPEG', quality=85)
        return output.getvalue()
    except Exception as exc:
        raise ValueError('Unable to decode selfie image.') from exc


def compare_faces(
    source_image_url: str,
    target_image_base64: str,
    similarity_threshold: float = 75.0
) -> dict:
    try:
        print(f"Downloading registration photo: {source_image_url}")

        if not source_image_url or not isinstance(source_image_url, str):
            return {
                "match": False,
                "confidence": 0,
                "message": "Invalid registration photo URL",
            }

        parsed = urlparse(source_image_url.strip())
        if parsed.scheme not in ("http", "https"):
            return {
                "match": False,
                "confidence": 0,
                "message": f"Invalid registration photo URL: {source_image_url}",
            }

        response = requests.get(
            source_image_url,
            timeout=15,
            headers={"User-Agent": "ALM-Voting/1.0"}
        )

        print(f"Photo download status: {response.status_code}")
        print(f"Photo size: {len(response.content)} bytes")

        if response.status_code != 200:
            return {
                "match": False,
                "confidence": 0,
                "message": f"Could not load registration photo (status {response.status_code})",
            }

        source_bytes = response.content
        if not source_bytes:
            return {
                "match": False,
                "confidence": 0,
                "message": "Registration photo is empty",
            }

        selfie_b64 = target_image_base64
        if selfie_b64 is None:
            return {
                "match": False,
                "confidence": 0,
                "message": "Selfie image data is missing",
            }

        if "," in selfie_b64:
            selfie_b64 = selfie_b64.split(",", 1)[1]

        try:
            target_bytes = base64.b64decode(selfie_b64)
        except Exception as exc:
            return {
                "match": False,
                "confidence": 0,
                "message": f"Invalid selfie image encoding: {exc}",
            }

        print(f"Selfie decoded size: {len(target_bytes)} bytes")

        try:
            img = Image.open(BytesIO(target_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            target_bytes = buffer.getvalue()
            print(f"Selfie converted to JPEG: {len(target_bytes)} bytes")
        except Exception as pil_err:
            print(f"PIL conversion warning: {pil_err}")

        print("Calling AWS Rekognition compare_faces...")
        client = get_rekognition_client()

        result = client.compare_faces(
            SourceImage={"Bytes": source_bytes},
            TargetImage={"Bytes": target_bytes},
            SimilarityThreshold=similarity_threshold,
        )

        print(f"AWS Raw result: {result}")

        face_matches = result.get("FaceMatches", [])
        unmatched = result.get("UnmatchedFaces", [])

        print(f"Face matches: {len(face_matches)}")
        print(f"Unmatched faces: {len(unmatched)}")

        if face_matches:
            best = max(face_matches, key=lambda x: x.get("Similarity", 0))
            confidence = round(float(best.get("Similarity", 0.0)), 1)
            return {
                "match": True,
                "confidence": confidence,
                "message": f"Identity verified — {confidence}% match",
            }

        if not unmatched:
            return {
                "match": False,
                "confidence": 0,
                "message": "No face detected in your selfie. Please ensure good lighting and face the camera directly.",
            }

        return {
            "match": False,
            "confidence": 0,
            "message": "Face does not match your profile photo. Please try again.",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"compare_faces error: {str(e)}")
        return {
            "match": False,
            "confidence": 0,
            "message": f"Verification error: {str(e)}",
        }
