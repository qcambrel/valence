import os
import json
import uuid
import tempfile
import subprocess

import cv2
import boto3
import torch
import runpod
import numpy as np

from diffusers import StableVSRPipeline
from huggingface_hub import login

hf_token = os.environ.get("HF_TOKEN")
if hf_token is None:
    raise ValueError("HF_TOKEN is not set")

login(token=hf_token)

model = "claudiom4sir/StableVSR"
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32
pipe = StableVSRPipeline.from_pretrained(model, torch_dtype=dtype).to(device)
pipe.enable_attention_slicing()
pipe.set_progress_bar_config(disable=True)

s3_client = boto3.client("s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

class VideoDownloader:
    def __init__(self, url: str, tmpdir: str, client: boto3.client = None):
        self.tmpdir = tmpdir
        self.url = url
        self.client = client
        self.bucket = None
        self.key = None

    def download(self) -> str:
        if self.url.startswith("s3://"):
            bucket, key = self.url[5:].split("/", 1)
            self.bucket = bucket
            self.key = key
            local_path = os.path.join(self.tmpdir, key)
            self.client.download_file(bucket, key, local_path)
        else:
            local_path = os.path.join(self.tmpdir, os.path.basename(self.url))
            subprocess.run(["yt-dlp", self.url, "-o", local_path])

        return "Download successful", local_path
    
class VideoUploader:
    def __init__(self, path: str, url: str, client: boto3.client = None, expire: int = 3600):
        self.path = path
        self.url = url
        self.client = client
        self.expire = expire

    def upload(self) -> str:
        if self.url.startswith("s3://"):
            bucket, key = self.url[5:].split("/", 1)
            self.bucket = bucket
            self.key = key
        self.client.upload_file(self.path, self.bucket, self.key, ExtraArgs={"ContentType": "video/mp4"})
        presigned_url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self.key},
            ExpiresIn=self.expire
        )
        return "Upload successful", {"presigned_url": presigned_url}

class VideoPreprocessor:
    def __init__(self, video_path: str, tmpdir: str):
        self.tmpdir = tmpdir
        self.video_path = video_path
        self.frames = []

    def extract_frames(self) -> tuple[list[np.ndarray], list[str]]:
        frames_dir = os.path.join(self.tmpdir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        subprocess.run(["ffmpeg", "-i", self.video_path, os.path.join(frames_dir, "%.08d.png")])
        paths = sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith(".png")])
        self.frames = [cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB) for p in paths]
        return self.frames, paths

class VideoEncoder:
    def __init__(self, frames: list[np.ndarray], out_path: str, fps: int = 30):  
        self.frames = frames
        self.out_path = out_path
        self.fps = fps

    def encode_video(self) -> str:
        height, width, _ = self.frames[0].shape
        tmpdir = os.path.dirname(self.out_path)
        seqdir = os.path.join(tmpdir, "out_frames")
        os.makedirs(seqdir, exist_ok=True)
        for i, frame in enumerate(self.frames):
            cv2.imwrite(os.path.join(seqdir, f"{i:08d}.png"), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
        subprocess.run([
            "ffmpeg",
            "-framerate", f"{self.fps}",
            "-i", os.path.join(seqdir, "%08d.png"),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            self.out_path
        ])

        return "Encoding successful", self.out_path
    
class VSRWorker:
    def __init__(self, frames, scale_factor: float = 2.0, num_inference_steps: int = 25, guidance_scale: float = 1.0, fps: int = 30):
        self.frames = frames
        self.scale_factor = scale_factor
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.fps = fps
    
    def _chunk(self, seq, window=32, stride=28):
        i = 0
        n = len(seq)
        while i < n:
            end = min(i + window, n)
            yield i, end, seq[i:end]
            if end == n:
                break
            i += stride

    def run(self):
        up_frames = []
        pipe_kwargs = {
            "scale": self.scale_factor,
            "num_inference_steps": self.num_inference_steps,
            "guidance_scale": self.guidance_scale
        }
        for start, end, chunk in self._chunk(self.frames):
            with torch.inference_mode(), torch.autocast("cuda", enabled=(device == "cuda")):
                out = pipe(chunk, **pipe_kwargs)
            out_frames = out.frames
            if start > 0:
                overlap = start - (len(up_frames))
                if overlap < 0:
                    out_frames = out_frames[-(end - start - (len(up_frames) - start)):]
            up_frames += out_frames
        return up_frames
        

def handler(event, context):
    body = event["input"]
    video_url = body["video_url"]
    output_url = body["output_url"]
    fps = body.get("fps", 30)
    scale_factor = body.get("scale_factor", 2.0)
    num_inference_steps = body.get("num_inference_steps", 25)
    guidance_scale = body.get("guidance_scale", 1.0)

    with tempfile.TemporaryDirectory() as tmpdir:
        video_downloader = VideoDownloader(video_url, tmpdir, client=s3_client)
        _, video_path = video_downloader.download()
        video_preprocessor = VideoPreprocessor(video_path, tmpdir)
        frames, _ = video_preprocessor.extract_frames()
        vsr_worker = VSRWorker(frames, scale_factor, num_inference_steps, guidance_scale, fps)
        frames = vsr_worker.run()
        out_path = os.path.join(tmpdir, os.path.basename(output_url))
        encoder = VideoEncoder(frames, out_path, fps)
        _ = encoder.encode_video()
        video_uploader = VideoUploader(out_path, output_url, client=s3_client)
        _, info = video_uploader.upload()

    return {"status": "ok", "info": info}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})