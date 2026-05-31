"""Wire a REAL AImyMusic Suno track through the Avatar House Band.

Resolves a track's audio (a `songs.audio_path` — a CDN URL or a signed bucket URL), runs the real
beat detection + band arranger, and renders to the Mac-side null target. The vocalist's lip-sync uses
a stand-in stream (real Audio2Face-3D needs NVIDIA_API_KEY + the live transport); the visual render
needs the Windows/RTX box. Everything else is genuine.

    # against the live catalog (needs SUPABASE_SERVICE_KEY):
    python examples/suno_band.py --track <songs.id>

    # against any audio URL (no credentials):
    python examples/suno_band.py --url https://cdn1.suno.ai/<id>.mp3 --title "Song"

    # show the band's beat grid (first bars) instead of a summary:
    python examples/suno_band.py --grid

Requires ffmpeg on PATH (used to decode the source audio for beat detection).
"""
from __future__ import annotations
import argparse
import os
import subprocess
import tempfile
import urllib.request

from ace_reel.band.arranger import BandArranger
from ace_reel.band.performance import BandPerformance
from ace_reel.band.roster import load_band
from ace_reel.contracts.interfaces import MusicSource, AceClient, Track
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.motion.beat import BeatResult, detect_beats
from ace_reel.render.band_base import NullBandRenderTarget

# A known public track so the example runs out of the box.
_DEFAULT_URL = "https://cdn1.suno.ai/cea04294-6b20-4306-8ef9-3d752ef958cf.mp3"
_DEFAULT_TITLE = "The Heart of Gold"
_ROLE_ORDER = {"vocals": 0, "drums": 1, "bass": 2, "guitar": 3, "keys": 4}


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ace-reel-avatars"})
    with urllib.request.urlopen(req) as r:
        return r.read()


def _to_wav(audio: bytes) -> bytes:
    """Decode any source codec to mono 22.05 kHz WAV so librosa beat detection is reliable."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-ac", "1", "-ar", "22050", "-f", "wav", "pipe:1"],
        input=audio, check=True, stdout=subprocess.PIPE,
    )
    return p.stdout


class _StandInVocals(AceClient):
    """Placeholder for Audio2Face-3D lip-sync (real A2F needs NVIDIA_API_KEY + live transport)."""
    def __init__(self, frames: int):
        self._frames = frames

    def stream(self, pcm_16k_mono: bytes, emotions=None):
        for i in range(self._frames):
            yield AnimationFrame(timestamp_s=i / 30,
                                 blendshapes={"JawOpen": 0.5 if i % 2 else 0.1},
                                 emotions={}, body_pose=None)


def _resolve_track(track_id: str | None, url: str, title: str) -> tuple[Track, bytes]:
    """From the live catalog when --track + creds are given; otherwise straight from a URL."""
    if track_id:
        from ace_reel.music.aimymusic_suno import AImyMusicSunoSource
        src = AImyMusicSunoSource.from_env()       # needs SUPABASE_* env; uses the fixed URL handling
        track = src.get_track(track_id)
        return track, src.read_audio(track)
    return Track(id="url", title=title, duration_s=0, audio_url=url), _download(url)


def _beats(wav: bytes) -> BeatResult:
    tmp = tempfile.mktemp(suffix=".wav")
    with open(tmp, "wb") as f:
        f.write(wav)
    try:
        return detect_beats(tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _print_summary(band, track, beats, arrangement, vocal_frames) -> None:
    cues = sum(len(c) for c in arrangement.values())
    print(f'{band.name} performing "{track.title}"  ({beats.bpm:.0f} BPM):')
    print(f"  vocals  {band.vocalist.avatar:14s} lip-syncs the lead ({vocal_frames} frames)")
    for member, member_cues in sorted(arrangement.items(), key=lambda kv: _ROLE_ORDER[kv[0].role.value]):
        print(f"  {member.role.value:7s} {member.avatar:14s} {len(member_cues):4d} cues  "
              f"({', '.join(member.clips)})")
    print(f"  total instrument cues: {cues}")


def _print_grid(band, track, beats, arrangement, bars: int = 4) -> None:
    times = beats.beat_times_s[:bars * 4]

    def row(cues):
        hits = {min(range(len(times)), key=lambda i: abs(times[i] - c.start_s))
                for c in cues if c.start_s <= times[-1] + 0.01}
        return " ".join("X" if i in hits else "." for i in range(len(times)))

    print(f'\n{band.name}  -  "{track.title}"  ({beats.bpm:.0f} BPM)  |  first {len(times) // 4} bars\n')
    print("        " + " ".join(("|" if i % 4 == 0 else str((i % 4) + 1)) for i in range(len(times))) + "   beat")
    print(f"vocals  " + "~ " * len(times) + f"  {band.vocalist.avatar} (lip-sync)")
    for member, cues in sorted(arrangement.items(), key=lambda kv: _ROLE_ORDER[kv[0].role.value]):
        print(f"{member.role.value:7s} " + row(cues) + f"   {member.avatar}")
    print("\nX = hit on that beat   ~ = continuous lip-sync")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Avatar House Band against a real Suno track.")
    ap.add_argument("--track", help="songs.id from the live catalog (needs SUPABASE_SERVICE_KEY)")
    ap.add_argument("--url", default=_DEFAULT_URL, help="direct audio URL (no credentials)")
    ap.add_argument("--title", default=_DEFAULT_TITLE)
    ap.add_argument("--band", default="bands/house.json")
    ap.add_argument("--grid", action="store_true", help="show the band's beat grid instead of a summary")
    args = ap.parse_args()

    track, raw = _resolve_track(args.track, args.url, args.title)
    wav = _to_wav(raw)
    beats = _beats(wav)
    band = load_band(args.band)
    arrangement = BandArranger().arrange(beats, band)

    # Render through the real BandRenderTarget contract (Mac-side null sink).
    frame_count = (track.duration_s or 100) * 30        # ~30 lip-sync frames/sec
    target = NullBandRenderTarget()
    target.run(BandPerformance(track=track, audio_pcm=wav, vocalist=band.vocalist,
                               vocal_frames=_StandInVocals(frame_count).stream(b""),
                               instrument_arrangement=arrangement))

    if args.grid:
        _print_grid(band, track, beats, arrangement)
    else:
        _print_summary(band, track, beats, arrangement, len(target.vocal_received))


if __name__ == "__main__":
    main()
