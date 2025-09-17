# import os

# import boto3
# import pytest

# from moto import mock_aws

# from app.config import settings
# from app.presign import presign_get, presign_put

# @pytest.fixture(autouse=True)
# def _aws_env(monkeypatch):
#     monkeypatch.setenv("AWS_REGION", "us-east-1")
#     monkeypatch.setenv("S3_BUCKET", "test-bucket")

#     import app.config as config
#     from importlib import reload

#     reload(config)
#     global settings

#     settings = config.settings

# @mock_aws
# def test_presign_urls():
#     s3_client = boto3.client("s3", region_name=settings.aws_region)
#     s3_client.create_bucket(Bucket=settings.bucket)
#     put_url = presign_put("uploads/test.mp4")
#     get_url = presign_get("uploads/test.mp4")
#     assert put_url.startswith("https://")
#     assert get_url.startswith("https://")

APIH = {"X-API-Key": "test"}

def test_presign_upload_and_download(app_client, s3_setup):
    # Upload presign
    r = app_client.post("/presign/upload?object_key=uploads/test.mp4", headers=APIH)
    assert r.status_code == 200
    assert r.json()["upload_url"].startswith("http")

    # Download presign
    r2 = app_client.get("/presign/download?object_key=uploads/test.mp4", headers=APIH)
    assert r2.status_code == 200
    assert r2.json()["download_url"].startswith("http")
