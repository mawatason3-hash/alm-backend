"""
Rekognition integration disabled.

This placeholder preserves the original file for audit/history but raises if used.
Rename back to `rekognition.py` only if you intend to re-enable AWS Rekognition.
"""

def compare_faces(*args, **kwargs):
    raise RuntimeError("Rekognition integration has been disabled. This function should not be called.")

def get_rekognition_client(*args, **kwargs):
    raise RuntimeError("Rekognition integration has been disabled.")
