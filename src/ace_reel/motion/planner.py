"""Turn detected beats into a beat-synced dance-clip timeline (consumed by the render engine)."""
from __future__ import annotations
from dataclasses import dataclass
from ace_reel.motion.beat import BeatResult


@dataclass(frozen=True)
class ClipCue:
    clip_name: str
    start_s: float
    energy: float          # 0..1, drives playback rate / amplitude in-engine


def plan_dance(beats: BeatResult, clips: list[str], beats_per_bar: int = 4) -> list[ClipCue]:
    if not clips:
        raise ValueError("need at least one dance clip")
    energy = min(1.0, max(0.0, (beats.bpm - 60) / 120))   # 60bpm->0, 180bpm->1
    cues: list[ClipCue] = []
    for bar_idx, i in enumerate(range(0, len(beats.beat_times_s), beats_per_bar)):
        cues.append(ClipCue(clip_name=clips[bar_idx % len(clips)],
                            start_s=beats.beat_times_s[i], energy=energy))
    return cues
