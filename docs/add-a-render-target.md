# Add a Render Target

The template spine is designed so you can swap or add render backends without touching the orchestrator, the ACE client, or the music source. This guide walks through the three steps: implement the interface, register it in the CLI, and test it.

## The interface

Every render target implements three methods. The `run()` method is inherited and calls them in order.

```python
from ace_reel.contracts.interfaces import RenderTarget
from ace_reel.contracts.frame import AnimationFrame

class RenderTarget(ABC):
    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None: ...
    def push(self, frame: AnimationFrame) -> None: ...
    def close(self) -> None: ...

    # inherited — do not override unless you have a good reason
    def run(self, avatar_asset: str, audio: bytes, frames: Iterable[AnimationFrame]) -> None:
        self.open(avatar_asset, audio)
        try:
            for f in frames:
                self.push(f)
        finally:
            self.close()
```

- `open` is called once before any frames arrive. `audio_pcm_16k_mono` is the full PCM buffer (16 kHz, mono, s16le) so the engine can start playback in sync.
- `push` is called once per `AnimationFrame` in timestamp order.
- `close` is called once after all frames, even if `push` raised.

## Reference implementation: NullRenderTarget

`src/ace_reel/render/base.py` is the simplest possible implementation. It records everything in memory and makes no external calls. Read it before writing your own.

```python
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
```

## Real-engine example: UnrealRenderTarget

`src/ace_reel/render/unreal_livelink.py` is the stub for the UE5 + ACE plugin path. It conforms to the interface but raises `NotImplementedError` until completed on a Windows/RTX box. Its docstring captures the verified UE wiring from Phase 0. Use it as a template for what `open` must do in a real engine target (establish a connection, load the avatar, begin audio playback) and what `push` must do (send the blendshape + emotion data to the engine per frame).

## Skeleton for a new target

```python
# src/ace_reel/render/my_target.py
from __future__ import annotations
from ace_reel.contracts.interfaces import RenderTarget
from ace_reel.contracts.frame import AnimationFrame


class MyRenderTarget(RenderTarget):

    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None:
        # Connect to the engine / device, load the avatar, start audio.
        # Called once before push().
        ...

    def push(self, frame: AnimationFrame) -> None:
        # Send one frame to the engine.
        # frame.blendshapes is a dict[str, float] keyed on ARKit-52 names.
        # frame.emotions is a dict[str, float] with the 10 A2F emotion channels.
        # frame.timestamp_s is the position in the audio stream in seconds.
        ...

    def close(self) -> None:
        # Flush and disconnect. Called even if push() raised.
        ...
```

## Register it in the CLI

The CLI factory function `_render()` in `src/ace_reel/cli.py` is the only place you need to change:

```python
def _render(engine: str):
    if engine == "null":
        return NullRenderTarget()
    if engine == "unreal":
        return UnrealRenderTarget()
    if engine == "my_engine":
        from ace_reel.render.my_target import MyRenderTarget
        return MyRenderTarget()
    raise ValueError(f"unknown engine: {engine}")
```

Add `"my_engine"` to the `click.Choice` list on the `--engine` option:

```python
@click.option("--engine", type=click.Choice(["null", "unreal", "my_engine"]), default="null")
```

Then run:

```bash
perform --track <id> --avatar <name> --engine my_engine
```

## Test it

Follow the `NullRenderTarget` test in `tests/test_render.py` as the pattern:

```python
from ace_reel.render.my_target import MyRenderTarget
from ace_reel.contracts.frame import AnimationFrame

def _frame(ts):
    return AnimationFrame(timestamp_s=ts, blendshapes={"JawOpen": 0.3}, emotions={}, body_pose=None)

def test_my_target_open_push_close():
    t = MyRenderTarget()
    t.run("Avatar_Name", b"\x00\x00", [_frame(0.0), _frame(0.033)])
    # assert whatever your target records / produces
```

Run the non-live suite to confirm nothing breaks:

```bash
python -m pytest -m "not live" -q
```
