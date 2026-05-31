"""MusicSource over the AImyMusic Suno library (Supabase songs + personal-library bucket)."""
from __future__ import annotations
import os
import urllib.request
from ace_reel.contracts.interfaces import MusicSource, Track


class SupabaseGateway:
    """Thin seam over supabase-py + storage (kept tiny so the source is testable with a fake)."""
    def __init__(self, url: str, key: str, bucket: str):
        from supabase import create_client
        self._sb = create_client(url, key)
        self._bucket = bucket

    def fetch_song(self, track_id: str) -> dict:
        res = self._sb.table("songs").select(
            "id,title,duration_seconds,audio_path").eq("id", track_id).single().execute()
        return res.data

    def sign_url(self, path: str) -> str:
        signed = self._sb.storage.from_(self._bucket).create_signed_url(path, 3600)
        url = signed.get("signedURL") or signed.get("signedUrl")  # storage3 key has varied by version
        if not url:
            raise RuntimeError(f"no signed URL returned for {path!r}: {signed!r}")
        return url

    def download(self, url: str) -> bytes:
        with urllib.request.urlopen(url) as r:
            return r.read()


class AImyMusicSunoSource(MusicSource):
    def __init__(self, gateway) -> None:
        self._gw = gateway

    @classmethod
    def from_env(cls) -> "AImyMusicSunoSource":
        return cls(SupabaseGateway(os.environ["SUPABASE_URL"],
                                   os.environ["SUPABASE_SERVICE_KEY"],
                                   os.environ.get("SUNO_AUDIO_BUCKET", "personal-library")))

    def get_track(self, track_id: str) -> Track:
        row = self._gw.fetch_song(track_id)
        path = row["audio_path"]
        # Some songs store a full CDN URL (e.g. https://cdn1.suno.ai/<id>.mp3); others store a
        # bucket-relative path that must be signed. Pass URLs through; sign the rest.
        audio_url = path if path.startswith(("http://", "https://")) else self._gw.sign_url(path)
        return Track(id=row["id"], title=row["title"],
                     duration_s=int(row["duration_seconds"] or 0),
                     audio_url=audio_url, bpm=None)

    def read_audio(self, track: Track) -> bytes:
        return self._gw.download(track.audio_url)
