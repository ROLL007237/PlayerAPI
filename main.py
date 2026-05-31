import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

def get_spotify_client() -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI", "http://localhost:5000/callback"),
        scope="playlist-read-private playlist-read-collaborative",
        cache_path=".spotify_token_cache"
    ))


def parse_playlist_tracks(playlist_id: str, sp: spotipy.Spotify):
    tracks = []
    offset = 0

    while True:
        response = sp.playlist_items(
            playlist_id,
            limit=100,
            offset=offset,
            fields="items(track(name,album(release_date))),next",
            additional_types=["track"]
        )

        for item in response.get("items", []):
            track = item.get("track")
            if track and track.get("name") and track.get("album", {}).get("release_date"):
                tracks.append({
                    "name": track["name"],
                    "year": int(track["album"]["release_date"][:4])
                })

        if response.get("next") is None:
            break

        offset += 100

    return tracks


class Track(BaseModel):
    name: str
    year: int

class PlaylistResponse(BaseModel):
    playlist_id: str
    total: int
    tracks: list[Track]


@app.get("/playlist/{playlist_id}/tracks", response_model=PlaylistResponse)
def get_playlist_tracks(playlist_id: str):
    """
    Returns all tracks from a Spotify playlist in {name, year} format.

    - **playlist_id**: Spotify playlist ID (e.g. 6kXjeKURGZ0Dug50hUsiDf)
    """
    try:
        sp = get_spotify_client()
        tracks = parse_playlist_tracks(playlist_id, sp)
        return PlaylistResponse(
            playlist_id=playlist_id,
            total=len(tracks),
            tracks=tracks
        )
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 401:
            raise HTTPException(status_code=401, detail="Spotify authentication failed. Delete .spotify_token_cache and retry.")
        elif e.http_status == 403:
            raise HTTPException(status_code=403, detail="Access denied. Make sure the playlist is public or you have the right scopes.")
        elif e.http_status == 404:
            raise HTTPException(status_code=404, detail=f"Playlist '{playlist_id}' not found.")
        raise HTTPException(status_code=500, detail=str(e))

