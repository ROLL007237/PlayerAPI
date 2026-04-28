from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import shutil
import mimetypes

app = FastAPI(title="MP3 Player API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory track store (replace with a DB in production)
tracks_db: dict[str, dict] = {}

# Seed with some demo tracks
for i, demo in enumerate([
    {"title": "Midnight Drive", "artist": "The Neon Collective", "duration": 222},
    {"title": "Golden Hour",    "artist": "Solstice Radio",      "duration": 255},
    {"title": "Slow Burn",      "artist": "Luna Park",           "duration": 238},
    {"title": "Coastline",      "artist": "The Neon Collective", "duration": 302},
    {"title": "City Lights",    "artist": "Solstice Radio",      "duration": 208},
], 1):
    tid = str(uuid.uuid4())
    tracks_db[tid] = {
        "id": tid,
        "title": demo["title"],
        "artist": demo["artist"],
        "duration": demo["duration"],
        "file_path": None,
        "order": i,
    }


class TrackUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return 'mp3_player.html'


@app.get("/tracks")
def list_tracks():
    """Return all tracks sorted by insertion order."""
    sorted_tracks = sorted(tracks_db.values(), key=lambda t: t["order"])
    return [_public(t) for t in sorted_tracks]


@app.get("/tracks/{track_id}")
def get_track(track_id: str):
    """Return metadata for a single track."""
    track = _get_or_404(track_id)
    return _public(track)


@app.post("/tracks/upload", status_code=201)
async def upload_track(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    artist: Optional[str] = None,
):
    """Upload an MP3 file and register it as a track."""
    if not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only .mp3 files are accepted")

    track_id = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{track_id}.mp3")

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    track = {
        "id": track_id,
        "title": title or os.path.splitext(file.filename)[0],
        "artist": artist or "Unknown Artist",
        "duration": None,   # could parse with mutagen in a real app
        "file_path": dest,
        "order": len(tracks_db) + 1,
    }
    tracks_db[track_id] = track
    return _public(track)


@app.patch("/tracks/{track_id}")
def update_track(track_id: str, body: TrackUpdate):
    """Update title and/or artist of a track."""
    track = _get_or_404(track_id)
    if body.title is not None:
        track["title"] = body.title
    if body.artist is not None:
        track["artist"] = body.artist
    return _public(track)


@app.delete("/tracks/{track_id}", status_code=204)
def delete_track(track_id: str):
    """Delete a track and its uploaded file (if any)."""
    track = _get_or_404(track_id)
    if track["file_path"] and os.path.exists(track["file_path"]):
        os.remove(track["file_path"])
    del tracks_db[track_id]


@app.get("/tracks/{track_id}/stream")
def stream_track(track_id: str):
    """Stream the MP3 audio file for a track."""
    track = _get_or_404(track_id)
    if not track["file_path"] or not os.path.exists(track["file_path"]):
        raise HTTPException(status_code=404, detail="Audio file not found for this track")
    return FileResponse(
        track["file_path"],
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(track_id: str) -> dict:
    if track_id not in tracks_db:
        raise HTTPException(status_code=404, detail="Track not found")
    return tracks_db[track_id]


def _public(track: dict) -> dict:
    """Strip internal fields before returning to the client."""
    return {k: v for k, v in track.items() if k != "file_path"}
