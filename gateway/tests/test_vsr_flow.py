# import os

# import boto3
# import pytest

# from moto import mock_aws
# from fastapi.testclient import TestClient

# from app.main import app
# from app import vsr_client
# from app.config import settings
# from app.jobs import sign_hmac

# os.environ.setdefault("AWS_REGION", "us-east-1")
# os.environ.setdefault("S3_BUCKET", "test-bucket")
# os.environ.setdefault("GATEWAY_API_KEY", "test")
# os.environ.setdefault("MODERATION_ENABLED", "0")
# os.environ.setdefault("RUNPOD_ENDPOINT_ID", "test")
# os.environ.setdefault("RUNPOD_API_KEY", "test")

# client = TestClient(app)

# @mock_aws
# def test_vsr_path(monkeypatch):
#     s3_client = boto3.client("s3", region_name=settings.aws_region)
#     if settings.bucket:
#         s3_client.create_bucket(Bucket=settings.bucket)
#     else:


#     response = client.post(
#         "/presign/upload?object_key=uploads/test.mp4",
#         headers={"X-API-Key": "test"},
#     )
#     assert response.status_code == 200
#     put_url = response.json()["upload_url"]
    
#     if settings.bucket:
#         s3_client.put_object(Bucket=settings.bucket, Key="uploads/test.mp4", Body=b"data", ContentType="video/mp4")

#     def mock_run_vsr(input_url, webhook_url, **kwargs):
#         return {"status": "ok", "info": {}}
    
#     monkeypatch.setattr(vsr_client, "run_vsr", mock_run_vsr)

#     body = {
#         "object_key": "uploads/test.mp4",
#         "input_url": put_url,
#         "output_url": "s3://test-bucket/outputs/test.mp4",
#         "scale": 2,
#         "fps": 30,
#         "num_inference_steps": 25,
#         "guidance_scale": 1
#     }
#     response = client.post(
#         "/submit",
#         json=body,
#         headers={"X-API-Key": "test"},
#     )
#     assert response.status_code == 200
#     job_id = response.json()["job_id"]

#     sig = sign_hmac(settings.hmac_secret, job_id)
#     webhook_body = {
#         "status": "ok",
#         "output": {"presigned_url": "s3://test-bucket/outputs/test.mp4"},
#         "metrics": {"mode": "nr_fast", "sharp_mean": 42.0}
#     }
#     webhook_response = client.post(
#         f"/webhook/runpod?job_id={job_id}&sig={sig}",
#         json=webhook_body
#     )
#     assert webhook_response.status_code == 200

#     response_poll = client.get(
#         f"/status/{job_id}",
#         headers={"X-API-Key": "test"},
#     )
#     assert response_poll.status_code == 200
#     js = response_poll.json()
#     assert js["status"] == "SUCCEEDED"
#     assert js["output"]["presigned_url"] == "s3://test-bucket/outputs/test.mp4"
#     assert js["metrics"]["mode"] == "nr_fast"

import os
from app.jobs import sign_hmac

APIH = {"X-API-Key": "test"}

def test_async_submit_and_webhook(app_client, put_input_video, stub_runpod_async, monkeypatch):
    monkeypatch.setenv("MODERATION_ENABLED", "0")
    body = {
        "object_key": put_input_video,
        "scale": 2,
        "fps": 24,
        "num_inference_steps": 20,
        "metrics_mode": "nr_fast"
    }
    r = app_client.post("/submit", json=body, headers=APIH)
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    secret = os.environ["HMAC_SECRET"]
    sig = sign_hmac(secret, job_id)
    webhook_body = {
        "status": "ok",
        "output": {"presigned_url": "https://example.com/out.mp4"},
        "metrics": {"mode":"nr_fast","sharp_mean": 42.0}
    }
    r_web = app_client.post(f"/webhook/runpod?job_id={job_id}&sig={sig}", json=webhook_body)
    assert r_web.status_code == 200

    r_status = app_client.get(f"/status/{job_id}", headers=APIH)
    assert r_status.status_code == 200
    js = r_status.json()
    assert js["status"] == "SUCCEEDED"
    assert js["output"]["presigned_url"] == "https://example.com/out.mp4"
    assert js["metrics"]["mode"] == "nr_fast"
