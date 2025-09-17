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
