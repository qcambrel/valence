import io
import os
import uuid

import requests
import streamlit as st

gateway = os.environ.get("GATEWAY_URL", "http://localhost:8080")
api_key = os.environ.get("API_KEY", None)

st.set_page_config(
    page_title="Valence Playground",
    page_icon="🎥",
    layout="wide"
)
st.title("Valence Playground")

uploaded_file = st.file_uploader("Upload a video", type=["mp4"])
scale = st.selectbox("Scale", [2.0, 4.0], index=0)
fps = st.selectbox("FPS", [30, 60], index=0)
num_inference_steps = st.selectbox("Num Inference Steps", [25, 50], index=0)
guidance_scale = st.selectbox("Guidance Scale", [1.0, 2.0], index=0)

if st.button("Submit", disabled=(uploaded_file is None)):
    key = f"uploades/{uuid.uuid4().hex}.mp4"
    response = requests.post(
        f"{gateway}/presign/upload",
        params={"object_key": key},
        headers={"X-API-Key": api_key},
        timeout=30
    )
    response.raise_for_status()