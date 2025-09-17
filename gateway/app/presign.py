import boto3

from .config import settings
from .constants import CONTENT_TYPE_MP4

s3_client = boto3.client("s3", region_name=settings.aws_region)

def presign_put(object_key: str, expire: int = 900) -> str:
    return s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.bucket, 
            "Key": object_key, 
            "ContentType": CONTENT_TYPE_MP4
        },
        ExpiresIn=expire
    )

def presign_get(object_key: str, expire: int = 900) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.bucket,
            "Key": object_key
        },
        ExpiresIn=expire
    )