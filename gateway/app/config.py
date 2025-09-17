import os

from pydantic import BaseModel

class Settings(BaseModel):
    api_key: str | None = os.environ.get("GATEWAY_API_KEY", None)
    cors_allow_origins: list[str] = (
        os.environ.get("GATEWAY_CORS_ALLOW_ORIGINS", "*").split(",")
    )

    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    bucket: str = os.environ.get("S3_BUCKET", "test-bucket")

    moderation_enabled: bool = os.environ.get("MODERATION_ENABLED", "0") == "1"
    moderation_threshold: int = int(os.environ.get("MODERATION_THRESHOLD", "80"))
    moderation_timeout: int = int(os.environ.get("MODERATION_TIMEOUT", "600"))

    runpod_endpoint_id: str = os.environ.get("RUNPOD_ENDPOINT_ID", "ep")
    runpod_api_key: str = os.environ.get("RUNPOD_API_KEY", "rk")

    ddb_table: str | None = os.environ.get("DDB_TABLE", None)
    job_ttl_seconds: int = int(os.environ.get("JOB_TTL_SECONDS", "3600"))
    webhook_base_url: str = os.environ.get("WEBHOOK_BASE_URL", "")
    hmac_secret: str = os.environ.get("HMAC_SECRET", "change-me")

settings = Settings()