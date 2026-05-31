# Architecture

> ace-reel-avatars — engine-agnostic template spine for the NVIDIA ACE x Unreal singing/dancing avatar pipeline.

## The core decision: ACE is face-only

NVIDIA Audio2Face-3D (A2F-3D) produces ARKit-52 blendshapes + 10 emotion channels from audio. That is all it does. There is no NVIDIA service for audio→body or audio→dance; Audio2Gesture (Omniverse, upper-body gesture only) is discontinued. See `docs/00-discovery.md` §A for the full inventory.

**Dancing is therefore implemented as beat-synced motion clips.** `motion/beat.py` derives tempo and beat times from the song audio using librosa (the `songs` table has no BPM column). `motion/planner.py` converts that into a `ClipCue` timeline — a list of `(clip_name, start_s, energy)` structs the render engine uses to schedule pre-retargeted dance clips on the MetaHuman body. The face layer (from A2F) and the body layer (from motion clips) are blended in Unreal Engine 5, not in Python.

## Three-adapter design

All vendor types are confined behind three abstract interfaces. The only type that crosses boundaries is `AnimationFrame`.

```
MusicSource          AceClient            RenderTarget
(Supabase / any)     (A2F-3D / any)       (Unreal / null / any)
      |                    |                     |
      |   Track + audio    |  AnimationFrame[]   |
      +-------> Orchestrator -----> A2F ---------> Render
```

Each adapter is independently swappable:

| Interface | Production impl | Mac-runnable impl |
|---|---|---|
| `MusicSource` | `AImyMusicSunoSource` (Supabase `songs` + `personal-library`) | same (network-gated by `@live`) |
| `AceClient` | `A2FClient` + `NvcfA2FTransport` (hosted A2F gRPC) | `A2FClient` + `FakeTransport` (unit tests) |
| `RenderTarget` | `UnrealRenderTarget` (Win/RTX stub) | `NullRenderTarget` (records frames) |

## Data-flow diagram

```
┌─────────────────────────────────────────────────────┐
│                    Orchestrator                     │
│                                                     │
│  MusicSource.get_track(id)                          │
│       └─→ Track(id, title, duration_s, audio_url)  │
│                                                     │
│  MusicSource.read_audio(track)                      │
│       └─→ raw audio bytes (mp3/m4a, any codec)     │
│                                                     │
│  to_pcm_16k_mono_bytes(raw)  ←── ffmpeg subprocess │
│       └─→ PCM s16le mono 16 kHz bytes              │
│                                                     │
│  AceClient.stream(pcm)  ←── hosted gRPC to A2F-3D  │
│       └─→ Iterator[AnimationFrame]                  │
│             • timestamp_s                           │
│             • blendshapes  (ARKit-52, 52 keys)      │
│             • emotions     (10 channels, 0..1)      │
│             • body_pose    (None in v1)             │
│                                                     │
│  RenderTarget.run(avatar, pcm, frames)              │
│       ├─ open(avatar, pcm)                         │
│       ├─ push(frame) × N                           │
│       └─ close()                                   │
└─────────────────────────────────────────────────────┘

     motion pipeline (parallel, data only)
┌─────────────────────────────────────────────────────┐
│  detect_beats(audio_path)  ←── librosa              │
│       └─→ BeatResult(bpm, beat_times_s[])           │
│                                                     │
│  plan_dance(beats, clips, beats_per_bar)            │
│       └─→ ClipCue[](clip_name, start_s, energy)    │
│            ↓ consumed by the render engine          │
│            (IK-retargeted clips on MetaHuman body)  │
└─────────────────────────────────────────────────────┘
```

## Two run modes

**Streaming / orchestration mode (Mac-runnable):** The Orchestrator feeds audio into A2F-3D's gRPC bidirectional stream (`ProcessAudioStream`) and receives `AnimationFrame`s back in real time. With `--engine null`, frames go to `NullRenderTarget` (recorded in memory). This mode works on any machine and is what the 24 unit tests exercise.

**Offline reel mode (Windows/RTX):** The same Orchestrator feeds frames into `UnrealRenderTarget`, which forwards them to a running UE5 instance. UE5 bakes the face curve data into an Anim Sequence and renders via Movie Render Queue to a portrait video (1080×1920). This path requires Windows + NVIDIA RTX + UE 5.6 + ACE plugin 2.5. See `docs/setup-reel-engine.md`.

## File map

```
src/ace_reel/
  contracts/
    frame.py          AnimationFrame, ARKIT_52 tuple, EMOTIONS tuple
    interfaces.py     AceClient, RenderTarget, MusicSource ABCs; Track dataclass
  ace/
    blendshape_map.py to_arkit_dict(names, weights) → {name: weight}
    ace_client.py     A2FClient (transport seam), NvcfA2FTransport (hosted gRPC stub),
                      to_pcm_16k_mono(path) → bytes
  motion/
    beat.py           detect_beats(path) → BeatResult(bpm, beat_times_s)
    planner.py        plan_dance(beats, clips, beats_per_bar) → list[ClipCue]
  render/
    base.py           NullRenderTarget (records frames; Mac-runnable reference impl)
    unreal_livelink.py UnrealRenderTarget (interface-conforming stub; complete on Win/RTX)
  music/
    aimymusic_suno.py AImyMusicSunoSource over Supabase xltunldffphrlqstujyg
  orchestrator.py     Orchestrator.perform() + to_pcm_16k_mono_bytes()
  cli.py              `perform` click command; _render() factory
```

## AnimationFrame — the spine

Every adapter speaks `AnimationFrame` and nothing else crosses the boundary:

- `timestamp_s`: float — position in the audio stream (seconds)
- `blendshapes`: `dict[str, float]` — keys must be in `ARKIT_52`; values 0..1
- `emotions`: `dict[str, float]` — keys must be in `EMOTIONS`; values 0..1
- `body_pose`: `BodyPose | None` — skeletal joint quaternions; `None` in v1 (dance comes from motion clips, not from this field)

Pydantic v2 enforces all constraints at construction time. Unknown keys and out-of-range weights raise `ValidationError`.

## Band layer (Avatar House Band)

`src/ace_reel/band/` composes the spine into a multi-avatar performance: `roster` (Band/Member),
`arranger` (beats -> per-instrument ClipCue timelines, reusing `plan_dance`), `performance`
(BandPerformance), `orchestrator` (BandOrchestrator). The vocalist streams A2F face frames; each
instrumentalist gets a static beat-synced cue timeline. `render/band_base.py` (NullBandRenderTarget
+ Unreal stub) is the multi-avatar analogue of the single-avatar RenderTarget. Full design:
`docs/specs/2026-05-30-avatar-house-band-design.md`.
