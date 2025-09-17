from pydantic import BaseModel, Field, AnyHttpUrl

class PresignUploadOut(BaseModel):
    object_key: str
    upload_url: AnyHttpUrl

class PresignDownloadOut(BaseModel):
    download_url: AnyHttpUrl

class VSRRequest(BaseModel):
    object_key: str | None = Field(default=None, description="Key inside our BUCKET, e.g. uploads/123.mp4")
    input_url: AnyHttpUrl | None = None

    output_url: AnyHttpUrl | None = None

    scale: int = 2
    fps: int = 30
    num_inference_steps: int = 25
    guidance_scale: int = 1

    metrics_mode: str | None = Field(default="nr_fast", description="off|nr_fast|fr")
    reference_url: AnyHttpUrl | None = None

class VSRResponse(BaseModel):
    status: str
    info: dict | None = None

class SubmitRequest(BaseModel):
    object_key: str | None = None
    input_url: AnyHttpUrl | None = None
    output_url: AnyHttpUrl | None = None
    scale: int = 2
    fps: int = 30
    num_inference_steps: int = 25
    guidance_scale: int = 1
    metrics_mode: str | None = "nr_fast"
    reference_url: AnyHttpUrl | None = None

class SubmitResponse(BaseModel):
    job_id: str
    status: str = "SUBMITTED"

class StatusResponse(BaseModel):
    job_id: str
    status: str
    output: dict | None = None
    metrics: dict | None = None
    error: str | None = None