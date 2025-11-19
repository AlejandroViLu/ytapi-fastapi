from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re

app = FastAPI()

# Permitir peticiones desde Android
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Limpieza de título
def clean_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'\s+', '-', title)
    return title[:50]


@app.get("/")
def home():
    return {"status": "ok", "message": "YT API funcionando en Render!"}


@app.get("/info")
def get_video_info(url: str):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video = ydl.extract_info(url, download=False)

        title = video.get("title", "Sin título")
        duration = video.get("duration", 0)
        thumbnail = video.get("thumbnail", "")
        formats = video.get("formats", [])

        audio_formats = [
            f for f in formats if f.get("acodec") != "none"
        ]

        best_audio = max(audio_formats, key=lambda f: f.get("abr", 0))

        return {
            "title": title,
            "clean_title": clean_title(title),
            "duration": duration,
            "thumbnail": thumbnail,
            "audio_url": best_audio.get("url"),
            "audio_ext": best_audio.get("ext"),
            "abr": best_audio.get("abr"),
            "filesize": best_audio.get("filesize") or best_audio.get("filesize_approx"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
