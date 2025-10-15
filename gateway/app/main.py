import time 
import hmac
import hashlib
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.schemas import (
    SubmitRequest, SubmitResponse, VSRRequest, VSRResponse,
    StatusResponse, PresignUploadOut, PresignDownloadOut
)
from app.presign import presign_get, presign_put
from app.moderation import moderate_video
from app.vsr_client import run_vsr, RunpodError
from app.jobs import Jobs, sign_hmac

app = FastAPI(title="Valence Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

jobs = Jobs()

def auth(x_api_key: str):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/presign/upload", response_model=PresignUploadOut)
def presign_upload(object_key: str, x_api_key: str | None = Header(None)):
    auth(x_api_key)
    url = presign_put(object_key)
    return PresignUploadOut(object_key=object_key, upload_url=url)

@app.get("/presign/download", response_model=PresignDownloadOut)
def presign_download(object_key: str, x_api_key: str | None = Header(None)):
    auth(x_api_key)
    url = presign_get(object_key)
    return PresignDownloadOut(download_url=url)

@app.post("/submit", response_model=SubmitResponse)
def submit(request: SubmitRequest, x_api_key: str | None = Header(None)):
    auth(x_api_key)
    if request.input_url:
        input_url = str(request.input_url)
    elif request.object_key:
        if settings.moderation_enabled:
            ok, hits = moderate_video(request.object_key)
            if not ok:
                raise HTTPException(status_code=415, detail={"message": "Content rejected", "hits": hits})
        input_url = presign_get(request.object_key)
    else:
        raise HTTPException(status_code=400, detail="Object key or input URL is required")
    
    output_url = str(request.output_url) if request.output_url else None
    job = jobs.create(input_url=input_url, output_url=output_url)

    sig = sign_hmac(settings.hmac_secret,job.job_id)
    webhook = f"{settings.webhook_base_url}/webhook/runpod?job_id={job.job_id}&sig={sig}"

    try:
        vsr_job = run_vsr(
            input_url,
            webhook,
            output_url,
            request.scale,
            request.fps,
            request.num_inference_steps,
            request.metrics_mode,
            request.reference_url
        )
        jobs.mark_running(job_id=job.job_id, runpod_id=vsr_job["id"])
    except RunpodError as e:
        jobs.mark_failed(job_id=job.job_id, error=str(e))
        raise HTTPException(status_code=502, detail=str(e))
    
    return SubmitResponse(job_id=job.job_id)

@app.get("/status/{job_id}", response_model=StatusResponse)
def status(job_id: str, wait_ms: int | None = 0, x_api_key: str | None = Header(None)):
    auth(x_api_key)
    deadline = time.time() + (wait_ms or 0)/1000.0
    while True:
        item = jobs.get(job_id)
        if item and item.status in ("SUCCEEDED", "FAILED", "REJECTED"):
            return StatusResponse(**item.to_dict())
        if wait_ms and time.time() < deadline:
            time.sleep(1)
            continue
        if item:
            return StatusResponse(**item.to_dict())
        raise HTTPException(status_code=404, detail="Job not found")
    
@app.post("/webhook/runpod")
async def webhook_runpod(request: Request):
    qs = dict(request.query_params)
    job_id, sig = qs.get("job_id"), qs.get("sig")
    if not job_id or not sig or sig != sign_hmac(settings.hmac_secret, job_id):
        raise HTTPException(status_code=401, detail="Bad signature")
    body = await request.json()
    status = body.get("status")
    ok = status == "ok"
    output = body.get("output")
    metrics = body.get("metrics")
    error = body.get("error")
    jobs.update_from_result(job_id, ok=ok, output=output, metrics=metrics, error=error)
    return {"ok": True}