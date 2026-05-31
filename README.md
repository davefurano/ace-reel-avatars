# ace-reel-avatars

[![CI](https://github.com/davefurano/ace-reel-avatars/actions/workflows/ci.yml/badge.svg)](https://github.com/davefurano/ace-reel-avatars/actions/workflows/ci.yml)
[![Demo](https://github.com/davefurano/ace-reel-avatars/actions/workflows/demo.yml/badge.svg)](https://github.com/davefurano/ace-reel-avatars/actions/workflows/demo.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![NVIDIA Audio2Face-3D](https://img.shields.io/badge/NVIDIA-Audio2Face--3D-76b900.svg)](https://build.nvidia.com/nvidia/audio2face-3d)
[![Unreal Engine 5](https://img.shields.io/badge/Unreal%20Engine-5.6-313131.svg)](https://www.unrealengine.com/)

Engine-agnostic template spine for an NVIDIA ACE x Unreal Engine 5 singing/dancing avatar pipeline, fed by the AImyMusic Suno library.

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -m "not live" -q
```

Expected output: `45 passed` (single-avatar spine + the Avatar House Band layer).

Run a track through the null engine (Mac-runnable, no GPU, no Unreal):

```bash
cp .env.example .env
# edit .env: add NVIDIA_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
perform --track <songs.id> --avatar <avatar-name> --engine null
```

`songs.id` is a row ID from the Supabase `public.songs` table (project `xltunldffphrlqstujyg`). The null engine records all frames in memory and prints the frame count. It does not require a GPU or a running UE5 instance.

### Band mode (Avatar House Band)

Play a track through a fixed multi-avatar band (lead sings, instrumentalists move on-beat):

    perform        --track <id> --avatar <name> --engine null            # single avatar
    band-perform   --track <id> --band bands/house.json --engine null    # full band

`null` runs on the Mac (records the performance); `unreal` needs the Windows/RTX box.
Design: `docs/specs/2026-05-30-avatar-house-band-design.md`.

Two rosters ship in `bands/`: `house.json` (5-piece) and `demo_trio.json` (3-piece). Add your own
by copying the format — one `vocals` member plus instrumentalists with motion `clips`.

#### Demo (no credentials, no GPU, no Unreal)

`examples/demo_band.py` runs the Demo Trio against a self-generated 120 BPM click track — real beat
detection + arranger, a stand-in vocal stream, rendered to the Mac-side null target:

```bash
python examples/demo_band.py
```

```text
Demo Trio: 3 members (vocalist Avatar_Claire + 2 instrumentalists)
  vocal frames streamed : 30
  guitar Avatar_Mark    ->  4 cues (clips: strum_down, strum_up)
  drums  Avatar_Beat    -> 14 cues (clips: kick, snare)
  total instrument cues : 18
```

The drummer fires on every beat, the guitarist once per bar — both timed to the detected tempo. Swap
in `bands/house.json` (or your own roster), wire real Suno audio via `MusicSource`, and point
`--engine unreal` at the RTX box to see it rendered.

## The template story

One command. One config. Swap any layer without rewriting the others.

```
MusicSource  →  Orchestrator  →  AceClient  →  RenderTarget
(Supabase)        (Python)       (A2F-3D)     (null | unreal | yours)
```

Every layer is behind an abstract interface. The only type crossing boundaries is `AnimationFrame` — an engine-agnostic struct carrying ARKit-52 blendshapes, 10 emotion channels, and a timestamp.

- **Change the render engine:** implement `RenderTarget` (three methods: `open/push/close`), register it in `cli._render`. See `docs/add-a-render-target.md`.
- **Change the music source:** implement `MusicSource` (`get_track` + `read_audio`).
- **Change the A2F model:** set `A2F_FUNCTION_ID` in `.env` to a different model's function-id.

## Hardware reality

| Task | Where |
|---|---|
| Run unit tests | Mac (or any machine with Python 3.11+) |
| Stream audio to hosted A2F-3D | Mac — needs `NVIDIA_API_KEY` |
| Fetch tracks from Supabase | Mac — needs `SUPABASE_SERVICE_KEY` |
| Unreal Engine 5.6 + MetaHuman | Windows 10/11 + NVIDIA RTX GPU |
| ACE plugin 2.5 + face wiring | Windows/RTX only |
| Dance clip retarget (IK Retargeter) | Windows/RTX only |
| Reel export (Movie Render Queue, 1080×1920) | Windows/RTX only |

The Mac is the orchestration terminal. It runs Python, talks gRPC to the hosted A2F endpoint, and produces the `AnimationFrame` stream and `ClipCue` dance timeline. Unreal Engine 5 on a Windows/RTX machine does the actual render.

## What works today vs what needs the RTX box

| Feature | Status |
|---|---|
| `AnimationFrame` contract (ARKit-52 + emotions) | Works on Mac |
| Adapter interfaces (`AceClient`, `RenderTarget`, `MusicSource`) | Works on Mac |
| A2F blendshape map (A2F weight array → ARKit-52 dict) | Works on Mac |
| `A2FClient` core (transport seam + frame wrapping) | Works on Mac |
| `NvcfA2FTransport.process` (live hosted gRPC) | Needs `NVIDIA_API_KEY`; `nvidia-ace` package re-pin required — see `docs/setup-nvidia-ace.md` |
| Beat detection (`detect_beats` via librosa) | Works on Mac |
| Dance-clip planner (`plan_dance` → `ClipCue` timeline) | Works on Mac |
| `NullRenderTarget` (records frames, no engine) | Works on Mac |
| `AImyMusicSunoSource` (Supabase `songs` + `personal-library`) | Needs `SUPABASE_SERVICE_KEY` on Mac |
| `Orchestrator.perform` end-to-end | Works on Mac (with null engine + fake/live adapters) |
| `perform` CLI | Works on Mac with `--engine null` |
| `UnrealRenderTarget` (UE5 + ACE plugin 2.5) | Stub — needs Windows/RTX box to complete |
| IK-retargeted dance clips on MetaHuman body | Needs Windows/RTX box |
| Reel export via Movie Render Queue | Needs Windows/RTX box |

## Docs

- `docs/00-discovery.md` — Phase 0 findings: NVIDIA ACE inventory, hardware blockers, Supabase data layer
- `docs/01-architecture.md` — three-adapter design, data-flow diagram, file map
- `docs/setup-nvidia-ace.md` — get an API key, hosted vs self-hosted A2F, `nvidia-ace` package, running live tests
- `docs/setup-reel-engine.md` — UE 5.6 + ACE plugin 2.5 + MetaHuman + IK retarget + Movie Render Queue (Windows/RTX)
- `docs/add-a-render-target.md` — add a new render backend (the template extension payoff)

## Environment variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env`.

```bash
NVIDIA_API_KEY=nvapi-...
A2F_GRPC_ENDPOINT=grpc.nvcf.nvidia.com:443
A2F_FUNCTION_ID=<from build.nvidia.com>

SUPABASE_URL=https://xltunldffphrlqstujyg.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUNO_AUDIO_BUCKET=personal-library

RENDER_ENGINE=null
```

## Tests

```bash
# All non-live tests (45 tests, no external services needed):
python -m pytest -m "not live" -q

# Live A2F test (needs NVIDIA_API_KEY + tests/data/sample_vocal.wav):
python -m pytest tests/test_ace_client.py -v -m live

# Live Supabase test (needs SUPABASE_SERVICE_KEY + SUNO_TEST_TRACK_ID):
python -m pytest tests/test_music_source.py -v -m live
```
