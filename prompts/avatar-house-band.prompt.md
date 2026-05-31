# Build Prompt — Avatar House Band (fast rebuild)

> Paste into a fresh session at the repo root. This is a *distilled* prompt: the research is already
> done (see the verified facts below), so skip rediscovery and go straight to building. Goal: a song
> from the AImyMusic Suno catalog performed by a fixed multi-avatar band — lead vocalist lip-syncs
> (NVIDIA Audio2Face-3D), instrumentalists move/play on a beat grid — with the Unreal render as a
> documented Windows/RTX stub. Everything up to the render runs and is tested on a Mac.

## Mission
Build (or rebuild) an engine-agnostic Python "template spine" plus a band layer. Adapter boundaries
are sacred: ACE, the render engine, and the music library each sit behind a typed interface; the only
types that cross are `AnimationFrame`, `Track`, `ClipCue`, `Member`, `BandPerformance`. TDD every unit
(failing test first). No secrets in code (env + `.env.example`). Stubs raise `NotImplementedError`
with a doc pointer — never silently no-op.

## Verified facts — DO NOT re-research (cite docs only if something contradicts these)
- **Audio2Face-3D** = the singing lip-sync core. Container `nvcr.io/nim/nvidia/audio2face-3d:2.0`.
  Input PCM **mono 16-bit 16 kHz**; gRPC **bidirectional streaming** (`ProcessAudioStream`); output
  **ARKit-52 blendshapes (+extra tongue) + 10 emotions** (amazement, anger, cheekiness, disgust, fear,
  grief, joy, outofbreath, pain, sadness) at 30 FPS (regression) / 60 (diffusion). Hosted free at
  `grpc.nvcf.nvidia.com:443` via build.nvidia.com (API key + per-model function-id). SDK/UE plugin MIT.
- **NVIDIA ships NO audio→dance / audio→body service.** ACE is face-only. Dancing = librosa beat
  detection + curated motion clips, retargeted in UE5 (IK Retargeter on `metahuman_base_skel`).
- **Render = Windows + NVIDIA RTX only.** ACE Unreal plugin **2.5**, UE **5.6**, MetaHuman. Not macOS.
  Animation enters via the `Apply ACE Face Animations` Anim node → `Face_AnimBP`
  (`mh_arkit_mapping_pose_A2F`). NOT Live Link (deprecated). Reel export = Movie Render Queue (1080×1920).
- **Music data:** Supabase project `xltunldffphrlqstujyg`, table `public.songs` (~1,459 rows; columns
  `id, suno_id, title, duration_seconds, audio_path, lyrics, styles[]`). **`audio_path` is frequently a
  full `https://cdn1.suno.ai/<id>.mp3` URL (public, no key)** — only sometimes a `personal-library`
  bucket path. No BPM column (→ librosa). No vocal stem (→ feed full mix to A2F v1).

## Architecture (build exactly this; names are load-bearing)
```
src/ace_reel/
  contracts/  frame.py        AnimationFrame(timestamp_s, blendshapes, emotions, body_pose=None)
                              ARKIT_52, EMOTIONS; pydantic extra=forbid; ts>=0; sparse dicts OK
              interfaces.py   AceClient.stream / RenderTarget(open,push,close,preflight,run) /
                              MusicSource(get_track,read_audio) / Track(id,title,duration_s,audio_url,bpm=None)
  ace/        blendshape_map.py to_arkit_dict(names,weights)   ace_client.py A2FClient + NvcfA2FTransport(stub) + to_pcm_16k_mono
  motion/     beat.py detect_beats->BeatResult(bpm,beat_times_s)   planner.py plan_dance->ClipCue(clip_name,start_s,energy)
  render/     base.py NullRenderTarget   unreal_livelink.py UnrealRenderTarget(stub, preflight platform-guard)
              band_base.py BandRenderTarget + NullBandRenderTarget   unreal_band.py UnrealBandRenderTarget(stub)
  music/      aimymusic_suno.py AImyMusicSunoSource (SupabaseGateway seam; from_env)
  band/       roster.py Role/Member/Band/load_band   arranger.py BandArranger.arrange(beats,band)
              performance.py BandPerformance   orchestrator.py BandOrchestrator.perform(track_id,band)
  orchestrator.py Orchestrator + to_pcm_16k_mono_bytes   cli.py  `perform` + `band-perform`
bands/ house.json + demo_trio.json   examples/ demo_band.py + suno_band.py   tests/  .github/workflows/ci.yml+demo.yml
```
- `BandArranger.arrange` reuses `plan_dance` per instrumentalist at `ROLE_BEATS_PER_CUE = {drums:1, bass:2, guitar:4, keys:4}`; vocalist excluded.
- `BandOrchestrator`: get_track → read_audio → `to_pcm_16k_mono_bytes` → `detect_beats`(temp file, cleaned up) → arrange → vocal `ace.stream` → `BandPerformance` → `render.run`.

## Gotchas to bake in from the start (these cost review cycles last time)
1. `Member.clips` is a **tuple** and `Band.members` is a **tuple** → `Member` stays hashable (it's a dict key).
2. `Band.vocalist` raises **`ValueError`** if no vocalist (not bare `StopIteration`).
3. `preflight()` is the **CLI's** responsibility (fail fast for unreal-on-Mac); `run()` must NOT call it; `open()` re-guards platform.
4. CLI maps `NotImplementedError` + `(KeyError,ValueError,FileNotFoundError)` to `click.ClickException`; `--engine` uses `envvar="RENDER_ENGINE"`.
5. `AImyMusicSunoSource.get_track`: pass through `http(s)://` `audio_path` as-is; only `sign_url` bucket paths.
6. librosa can't reliably read mp3 with odd suffixes → decode to WAV via ffmpeg before `detect_beats` (see `examples/suno_band.py`).
7. `nvidia-ace` may not pip-install → keep it commented in `pyproject.toml`; `NvcfA2FTransport.process` stays a stub until a key + the pinned proto exist.
8. Live tests behind `@pytest.mark.live` skip cleanly without creds. Keep CI (`pytest -m "not live"`) + a Demo workflow green.

## Build order (TDD, commit per task)
1. Spine: contracts → ace (blendshape_map, A2FClient core + stub) → motion → render(null+unreal stub) → music → orchestrator → `perform` CLI.
2. Band layer: roster+load_band → arranger → performance → band render(null+unreal stub) → BandOrchestrator → `band-perform` CLI + `bands/*.json` (guard them with a test).
3. Examples: `demo_band.py` (synthetic, no creds) + `suno_band.py` (real `--track`/`--url`, `--grid` beat grid).
4. Infra: CI + Demo workflows (Node 24 actions), badges, LICENSE (MIT), CONTRIBUTING, CODE_OF_CONDUCT, README with the "what works today vs needs the RTX box" table.

## Acceptance
`pytest -m "not live"` all green; `python examples/demo_band.py` prints a performance; `python examples/suno_band.py --grid`
shows the band's beat grid against a real Suno track. Then (Windows/RTX, separate) implement
`UnrealBandRenderTarget.open/push_vocal_frame` against an in-engine bridge to actually render it.
