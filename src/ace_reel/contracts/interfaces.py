"""The three sacred adapter boundaries. No concrete vendor type may leak across these."""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from .frame import AnimationFrame


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    duration_s: int
    audio_url: str
    bpm: float | None = None


class MusicSource(ABC):
    """Yields Tracks (audio + metadata) from some library."""
    @abstractmethod
    def get_track(self, track_id: str) -> Track: ...
    @abstractmethod
    def read_audio(self, track: Track) -> bytes:
        """Return the raw source audio bytes (original codec; orchestrator transcodes)."""


class AceClient(ABC):
    """Turns 16 kHz mono PCM audio into a stream of engine-agnostic AnimationFrames."""
    @abstractmethod
    def stream(self, pcm_16k_mono: bytes, emotions: dict[str, float] | None = None
               ) -> Iterator[AnimationFrame]:
        """`emotions`, if given, must be a subset of frame.EMOTIONS with values in [0,1];
        concrete impls are responsible for honoring/validating it."""


class RenderTarget(ABC):
    """Engine-agnostic sink for AnimationFrames + the song audio. Concrete impls drive an engine."""
    @abstractmethod
    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None: ...
    @abstractmethod
    def push(self, frame: AnimationFrame) -> None: ...
    @abstractmethod
    def close(self) -> None: ...

    def run(self, avatar_asset: str, audio: bytes, frames: Iterable[AnimationFrame]) -> None:
        self.open(avatar_asset, audio)
        try:
            for f in frames:
                self.push(f)
        finally:
            self.close()
