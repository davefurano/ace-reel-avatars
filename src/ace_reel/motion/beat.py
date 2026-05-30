"""Tempo + beat-time detection via librosa (fallback for absent audio->dance service)."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import librosa


@dataclass(frozen=True)
class BeatResult:
    bpm: float
    beat_times_s: list[float]


def detect_beats(audio_path: str) -> BeatResult:
    y, sr = librosa.load(audio_path, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return BeatResult(bpm=float(np.asarray(tempo).item()),
                      beat_times_s=[float(t) for t in beat_times])
