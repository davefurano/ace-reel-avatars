"""Multi-avatar render contract: open a band scene, stream the vocalist's face, close."""
from __future__ import annotations
from abc import ABC, abstractmethod
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.band.roster import Member
from ace_reel.motion.planner import ClipCue
from ace_reel.band.performance import BandPerformance


class BandRenderTarget(ABC):
    @abstractmethod
    def open(self, members: list[Member], audio_pcm: bytes,
             instrument_arrangement: dict[Member, list[ClipCue]]) -> None: ...
    @abstractmethod
    def push_vocal_frame(self, frame: AnimationFrame) -> None: ...
    @abstractmethod
    def close(self) -> None: ...

    def preflight(self) -> None:
        """Optional early check (platform/deps) before any audio is processed; default no-op."""

    def run(self, perf: BandPerformance) -> None:
        self.preflight()
        members = [perf.vocalist, *perf.instrument_arrangement.keys()]
        try:
            self.open(members, perf.audio_pcm, perf.instrument_arrangement)
            for frame in perf.vocal_frames:
                self.push_vocal_frame(frame)
        finally:
            self.close()


class NullBandRenderTarget(BandRenderTarget):
    def __init__(self) -> None:
        self.opened_with: tuple[list[Member], int, dict] | None = None
        self.vocal_received: list[AnimationFrame] = []
        self.closed = False

    def open(self, members, audio_pcm, instrument_arrangement) -> None:
        self.opened_with = (members, len(audio_pcm), instrument_arrangement)

    def push_vocal_frame(self, frame) -> None:
        self.vocal_received.append(frame)

    def close(self) -> None:
        self.closed = True
