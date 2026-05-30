"""NullRenderTarget — engine-less sink used on the Mac and in tests."""
from __future__ import annotations
from ace_reel.contracts.interfaces import RenderTarget
from ace_reel.contracts.frame import AnimationFrame


class NullRenderTarget(RenderTarget):
    def __init__(self) -> None:
        self.opened_with: tuple[str, int] | None = None
        self.received: list[AnimationFrame] = []
        self.closed = False

    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None:
        self.opened_with = (avatar_asset, len(audio_pcm_16k_mono))

    def push(self, frame: AnimationFrame) -> None:
        self.received.append(frame)

    def close(self) -> None:
        self.closed = True
