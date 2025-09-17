APIH = {"X-API-Key": "test"}

def test_presign_upload_and_download(app_client, s3_setup):
    r = app_client.post("/presign/upload?object_key=uploads/test.mp4", headers=APIH)
    assert r.status_code == 200
    assert r.json()["upload_url"].startswith("http")

    r2 = app_client.get("/presign/download?object_key=uploads/test.mp4", headers=APIH)
    assert r2.status_code == 200
    assert r2.json()["download_url"].startswith("http")
