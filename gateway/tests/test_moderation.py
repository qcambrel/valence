APIH = {"X-API-Key": "secret"}

def test_submit_blocked_by_moderation(app_client_moderation_on, put_input_video, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "moderate_video", lambda key: (False, [{"Name":"Explicit Nudity","Confidence":99.0}]))

    r = app_client_moderation_on.post("/submit", json={"object_key": put_input_video}, headers=APIH)
    assert r.status_code == 415
    assert r.json()["detail"]["message"] == "Content rejected"