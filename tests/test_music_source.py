import os
import pytest
from ace_reel.music.aimymusic_suno import AImyMusicSunoSource
from ace_reel.contracts.interfaces import Track


class FakeGateway:
    def fetch_song(self, track_id):
        return {"id": track_id, "title": "Neon", "duration_seconds": 200,
                "audio_path": "songs/neon.mp3"}

    def sign_url(self, path):
        return f"https://signed/{path}"

    def download(self, url):
        return b"ID3audio"


def test_get_track_maps_row_to_track():
    src = AImyMusicSunoSource(gateway=FakeGateway())
    t = src.get_track("abc")
    assert isinstance(t, Track)
    assert t.title == "Neon" and t.duration_s == 200
    assert t.audio_url == "https://signed/songs/neon.mp3" and t.bpm is None


def test_read_audio_downloads_signed_url():
    src = AImyMusicSunoSource(gateway=FakeGateway())
    assert src.read_audio(src.get_track("abc")) == b"ID3audio"


class CdnGateway:
    """A song whose audio_path is already a full CDN URL (must NOT be signed)."""
    def fetch_song(self, track_id):
        return {"id": track_id, "title": "Heart of Gold", "duration_seconds": 100,
                "audio_path": "https://cdn1.suno.ai/abc.mp3"}
    def sign_url(self, path):
        raise AssertionError("sign_url must not be called for a full URL audio_path")
    def download(self, url):
        return b"mp3bytes"


def test_get_track_passes_through_full_cdn_url():
    src = AImyMusicSunoSource(gateway=CdnGateway())
    t = src.get_track("abc")
    assert t.audio_url == "https://cdn1.suno.ai/abc.mp3"   # used as-is, never signed
    assert src.read_audio(t) == b"mp3bytes"


@pytest.mark.live
def test_live_fetches_real_song():
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        pytest.skip("no SUPABASE_SERVICE_KEY")
    src = AImyMusicSunoSource.from_env()
    t = src.get_track(os.environ["SUNO_TEST_TRACK_ID"])
    assert t.title and t.audio_url.startswith("http")
