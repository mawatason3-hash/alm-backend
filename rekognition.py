import os
import base64
import requests
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from io import BytesIO
from PIL import Image


def _get_rekognition_client():
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    client_kwargs = {}

    if region:
        client_kwargs['region_name'] = region
    if aws_access_key_id:
        client_kwargs['aws_access_key_id'] = aws_access_key_id
    if aws_secret_access_key:
        client_kwargs['aws_secret_access_key'] = aws_secret_access_key

    return boto3.client('rekognition', **client_kwargs)


def fetch_image_bytes(image_url: str) -> bytes:
    if not image_url:
        raise ValueError('Image URL is required for verification.')

    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return response.content


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


def compare_faces(source_image_bytes: bytes, target_image_bytes: bytes, similarity_threshold: float = 75.0):
    if not source_image_bytes or not target_image_bytes:
        raise ValueError('Both source and target images are required for comparison.')

    client = _get_rekognition_client()
    try:
        response = client.compare_faces(
            SourceImage={'Bytes': source_image_bytes},
            TargetImage={'Bytes': target_image_bytes},
            SimilarityThreshold=similarity_threshold,
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f'Rekognition compare_faces failed: {exc}') from exc

    face_matches = response.get('FaceMatches', [])
    if not face_matches:
        unmatched = response.get('UnmatchedFaces', [])
        if not unmatched:
            return {
                'match': False,
                'similarity': 0.0,
                'confidence': 0.0,
                'distance': None,
                'message': 'No face detected in selfie',
            }
        return {
            'match': False,
            'similarity': 0.0,
            'confidence': 0.0,
            'distance': None,
            'message': 'Face does not match your profile photo',
        }

    best_match = max(face_matches, key=lambda match: match.get('Similarity', 0.0))
    similarity = float(best_match.get('Similarity', 0.0))
    confidence = float(best_match.get('Face', {}).get('Confidence', 0.0))
    distance = round(1.0 - similarity / 100.0, 4)
    match = similarity >= similarity_threshold

    return {
        'match': match,
        'similarity': similarity,
        'confidence': confidence,
        'distance': distance,
        'message': f'Identity verified — {similarity:.1f}% match' if match else 'Face does not match your profile photo',
    }
