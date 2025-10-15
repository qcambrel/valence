import time
import boto3
from app.config import settings
from app.constants import BLOCKED_CATEGORIES

rek_client = boto3.client("rekognition", region_name=settings.aws_region)

def start_moderation(object_key: str) -> str:
    response = rek_client.start_content_moderation(
        Video={
            "S3Object": {
                "Bucket": settings.bucket,
                "Name": object_key
            }
        }
    )
    return response["JobId"]

def wait_for_moderation(job_id: str, threshold: int, max_wait: int = None, sleep: int = 5) -> tuple[bool, list[dict]]:
    max_wait = max_wait or settings.moderation_timeout
    waited = 0
    next_token = None
    hits: list[dict] = []

    while waited < max_wait:
        if next_token:
            response = rek_client.get_content_moderation(JobId=job_id, NextToken=next_token)
        else:
            response = rek_client.get_content_moderation(JobId=job_id)
        
        status = response["JobStatus"]
        if status == "IN_PROGRESS":
            time.sleep(sleep)
            waited += sleep
            continue
        if status != "SUCCEEDED":
            return False, [{"Name": status or "UNKNOWN", "Confidence": 100.0}]
        
        for ev in response.get("ModerationLabels", []):
            label = ev.get("ModerationLabel", {})
            name = label.get("Name", "")
            confidence = float(label.get("Confidence", 0))
            if confidence >= threshold and name in BLOCKED_CATEGORIES:
                hits.append(label)
        
        next_token = response.get("NextToken")
        if not next_token:
            break
    
    return (len(hits) == 0), hits

def moderate_video(object_key: str) -> tuple[bool, list[dict]]:
    job_id = start_moderation(object_key)
    return wait_for_moderation(job_id, settings.moderation_threshold)
    
