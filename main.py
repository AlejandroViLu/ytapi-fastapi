from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import yt_dlp
import subprocess
import tempfile
import os
import re
import io


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
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"\s+", "-", title)
    return title[:50]


@app.get("/")
def home():
    return {"status": "ok", "message": "YT API funcionando en Render!"}


# --------------------------
# Obtener metadata
# --------------------------
@app.get("/info")
def get_video_info(url: str):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video = ydl.extract_info(url, download=False)

        title = video.get("title", "Sin título")
        duration = video.get("duration", 0)
        thumbnail = video.get("thumbnail", "")
        formats = video.get("formats", [])

        audio_formats = [f for f in formats if f.get("acodec") != "none"]

        best_audio = max(audio_formats, key=lambda f: f.get("abr", 0))

        return {
            "title": title,
            "clean_title": clean_title(title),
            "duration": duration,
            "thumbnail": thumbnail,
            "abr": best_audio.get("abr"),
            "ext": best_audio.get("ext"),
            "filesize": best_audio.get("filesize") or best_audio.get("filesize_approx"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --------------------------
# Descargar MP3 real
# --------------------------
@app.get("/audio")
def download_audio(url: str):

    # 1) Extraer info
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except:
        raise HTTPException(400, "No se pudo analizar el video.")

    title = clean_title(info.get("title", "audio"))
    tmp_dir = tempfile.mkdtemp()

    input_audio = os.path.join(tmp_dir, "raw.webm")
    output_mp3 = os.path.join(tmp_dir, f"{title}.mp3")

    # 2) Descargar audio puro
    download_opts = {
        "format": "bestaudio/best",
        "outtmpl": input_audio,
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])
    except:
        raise HTTPException(500, "Error al descargar el audio del video.")

    # 3) Convertir a MP3
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_audio, "-vn", "-acodec", "libmp3lame", "-b:a", "192k", output_mp3, "-y"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except:
        raise HTTPException(500, "Error al convertir el audio a MP3.")

    # 4) Leer MP3 y enviarlo al cliente
    try:
        mp3_bytes = open(output_mp3, "rb").read()
        buffer = io.BytesIO(mp3_bytes)

        return StreamingResponse(
            buffer,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'attachment; filename="{title}.mp3"'}
        )
    finally:
        try:
            os.remove(input_audio)
            os.remove(output_mp3)
            os.rmdir(tmp_dir)
        except:
            pass
