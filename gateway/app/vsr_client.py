import requests

from .config import settings

RUNSYNC_URL = f"https://api.runpod.ai/v2/{settings.runpod_endpoint_id}/runsync"
RUN_URL     = f"https://api.runpod.ai/v2/{settings.runpod_endpoint_id}/run"

class RunpodError(Exception):
    pass

def run_vsr(video_url: str, webhook_url: str, output_url: str | None, scale_factor: int, fps: int, num_inference_steps: int, metrics_mode: str | None = None, reference_url: str | None = None) -> dict:
    payload = {
        "input": {
            "video_url": video_url,
            "scale_factor": scale_factor,
            "num_inference_steps": num_inference_steps,
            "fps": fps
        },
        "webhook": webhook_url
    }
    if output_url:
        payload["input"]["output_url"] = output_url
    if metrics_mode:
        payload["input"]["metrics_mode"] = metrics_mode
    if reference_url:
        payload["input"]["reference_url"] = reference_url
    
    response = requests.post(
        RUN_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.runpod_api_key}"
        }, timeout=60
    )

    if response.status_code != 200:
        raise RunpodError(response.text)

    return response.json()