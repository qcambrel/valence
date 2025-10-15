APIH = {"X-API-Key": "secret"}

def test_webhook_rejects_bad_signature(app_client, put_input_video, stub_runpod_async, stub_rekognition):
    r = app_client.post("/submit", json={"object_key": put_input_video}, headers=APIH)
    job_id = r.json()["job_id"]
    # bad signature
    bad_sig = "deadbeef"
    r_web = app_client.post(f"/webhook/runpod?job_id={job_id}&sig={bad_sig}", json={"status":"ok"})
    assert r_web.status_code == 401
