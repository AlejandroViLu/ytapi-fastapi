from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import re

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'\s+', '-', title)
    return title[:60]

@app.get("/")
def home():
    return {"status": "ok", "message": "YT API funcionando correctamente"}

@app.get("/info")
def get_video_info(url: str):

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "extract_flat": False,
        "geo_bypass": True,
        "format": "bestaudio/best"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise HTTPException(status_code=400, detail="No se pudo obtener información del video.")

        title = info.get("title", "Sin titulo")
        duration = info.get("duration", 0)
        thumbnail = info.get("thumbnail", "")
        formats = info.get("formats", [])

        if not formats:
            raise HTTPException(status_code=400, detail="El video no tiene formatos disponibles.")

        # Filtrar solo formatos de audio
        audio_formats = [f for f in formats if f.get("acodec") and f["acodec"] != "none"]

        if not audio_formats:
            raise HTTPException(status_code=400, detail="No se encontraron formatos de audio.")

        # Elegir el mejor formato según bitrate o tamaño
        best_audio = max(
            audio_formats,
            key=lambda f: (f.get("abr") or 0, f.get("filesize") or 0)
        )

        return {
            "title": title,
            "clean_title": clean_title(title),
            "duration": duration,
            "thumbnail": thumbnail,
            "audio_url": best_audio.get("url"),
            "audio_ext": best_audio.get("ext"),
            "abr": best_audio.get("abr") or 0,
            "filesize": best_audio.get("filesize") or best_audio.get("filesize_approx") or 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar el video: {str(e)}")

@app.get("/audio")
def get_audio(url: str):

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "format": "bestaudio/best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise HTTPException(status_code=400, detail="No se pudo obtener información del audio.")

        return {
            "audio_url": info["url"],
            "title": info.get("title", "audio")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo procesar el audio: {str(e)}")
