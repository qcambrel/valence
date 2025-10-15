import os
import time
import threading
from app.jobs import sign_hmac

APIH = {"X-API-Key": "secret"}

def test_status_longpoll_returns_after_webhook(app_client, put_input_video, stub_runpod_async, stub_rekognition):
    # submit async job
    r = app_client.post("/submit",
        json={"object_key": put_input_video, "scale":2, "fps":24, "num_inference_steps":20, "metrics_mode":"nr_fast"},
        headers=APIH)
    job_id = r.json()["job_id"]

    # fire webhook shortly after
    secret = os.environ["HMAC_SECRET"]
    sig = sign_hmac(secret, job_id)
    webhook_body = {
        "status": "ok",
        "output": {"presigned_url": "https://example.com/out.mp4"},
        "metrics": {"mode":"nr_fast","sharp_mean": 40.0}
    }
    def _fire():
        time.sleep(0.2)
        app_client.post(f"/webhook/runpod?job_id={job_id}&sig={sig}", json=webhook_body)

    t = threading.Thread(target=_fire)
    t.start()

    # long-poll up to ~1.5s; handler sleeps in 1s chunks
    r_status = app_client.get(f"/status/{job_id}?wait_ms=1500", headers=APIH)
    t.join()
    assert r_status.status_code == 200
    assert r_status.json()["status"] == "SUCCEEDED"