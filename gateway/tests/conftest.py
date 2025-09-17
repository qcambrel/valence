import os
import importlib

import boto3
import pytest

from moto import mock_aws

@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Fake AWS creds for moto/boto3."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    yield

@pytest.fixture(scope="function")
def moto_aws(aws_credentials):
    with mock_aws():
        yield

@pytest.fixture(scope="function")
def env_defaults(monkeypatch):
    """Set env for the app under test (no config.settings references)."""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("GATEWAY_API_KEY", "test")
    monkeypatch.setenv("MODERATION_ENABLED", "0")  # off by default in tests
    monkeypatch.setenv("RUNPOD_ENDPOINT_ID", "ep")
    monkeypatch.setenv("RUNPOD_API_KEY", "rk")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "http://testserver")
    monkeypatch.setenv("HMAC_SECRET", "change-me")
    yield

@pytest.fixture(scope="function")
def s3_setup(moto_aws, env_defaults):
    """Create the test bucket in moto S3 (uses env only)."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    bucket = os.environ["S3_BUCKET"]
    print(f"Creating bucket {bucket} in region {region}")
    s3 = boto3.client("s3", region_name=region)
    s3.create_bucket(Bucket=bucket)
    return s3

@pytest.fixture(scope="function")
def app_client(s3_setup):
    """Return TestClient after env/mocks are ready."""
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    return TestClient(main.app)

@pytest.fixture(scope="function")
def app_client_moderation_on(monkeypatch, s3_setup):
    """Same as app_client, but with moderation enabled via env."""
    monkeypatch.setenv("MODERATION_ENABLED", "1")
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    return TestClient(main.app)

@pytest.fixture(scope="function")
def stub_runpod_async(monkeypatch):
    """Stub /run call to Runpod to return a fake run id."""
    from app import main
    def mock_run_vsr(input_url, webhook_url, output_url, *args):
        return {"status": "ok", "id": "123", "info": {}}
    monkeypatch.setattr(main, "run_vsr", mock_run_vsr)
    yield

@pytest.fixture(scope="function")
def put_input_video(s3_setup):
    """Upload a tiny dummy mp4 object into the test bucket; return its key."""
    bucket = os.environ["S3_BUCKET"]
    key = "uploads/test.mp4"
    print(f"Uploading {key} to {bucket}")
    s3_setup.put_object(Bucket=bucket, Key=key, Body=b"data", ContentType="video/mp4")
    return key
