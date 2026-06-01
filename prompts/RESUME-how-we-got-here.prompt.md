# RESUME — How We Got Here (ace-reel-avatars / Avatar House Band)

> Paste into a fresh session to pick up exactly where we left off. This is the narrative + state of
> everything built. Repo: github.com/davefurano/ace-reel-avatars (public, MIT, branch `main`).
> Working dir: ~/Desktop/08_aimyservice/aimymusicapp/ace-reel-avatars.

## The arc (how we got here)
1. **Started from a build prompt** at `prompts/nvidia-ace-unreal-engine-avatars.prompt.md` (turn a song
   into a photoreal avatar that sings + dances, NVIDIA ACE animation brain, Unreal render, AImyMusic Suno audio).
2. **Phase 0 discovery** (parallel research agents, grounded in live docs) found two decisive facts:
   ACE is **face-only** (no audio→dance service exists) and the render stack is **Windows + NVIDIA RTX only**
   — none of it runs on this Mac. Written to `docs/00-discovery.md`.
3. **Built the template spine** (Mac-runnable, TDD, subagent-driven with spec+quality review per layer):
   contracts → ace → motion → render → music → orchestrator → `perform` CLI. Pushed to a new public repo.
4. **Brainstormed → speced → planned → built the Avatar House Band** layer: a fixed 5-piece band (vocals +
   guitar/bass/drums/keys) where the vocalist lip-syncs (A2F) and instrumentalists move on a beat grid.
   Reuses the spine; no new deps. `band-perform` CLI + `bands/house.json` + `bands/demo_trio.json`.
5. **Added infra:** CI + Demo GitHub Actions (Node 24 actions), badges, MIT LICENSE, CONTRIBUTING.md.
6. **Wired a REAL Suno track:** discovered `songs.audio_path` is often a public `cdn1.suno.ai` URL → fixed
   `AImyMusicSunoSource` to pass URLs through; built `examples/suno_band.py` with a `--grid` beat-grid view.
   Proved it: "The Heart of Gold", 136 BPM → 413 instrument cues, real librosa tempo, real arrangement.
7. **Wrote forward artifacts:** `docs/SESSION-RECAP.md`, `prompts/avatar-house-band.prompt.md` (fast rebuild),
   `docs/runbook-cloud-rtx.md` (render on a Windows GPU VM), `prompts/hermes-two-agents.prompt.md` and a
   Hermes team-build prompt (spawn agents to learn ACE+Unreal / rebuild the whole pipeline).
8. **Recurring snag:** several turns trying to add `CODE_OF_CONDUCT.md` were interrupted by transient
   API/turn errors before the write landed. (Not a code bug, not content filtering — just turn failures.)

## Current state (verified)
- Tree clean, all pushed. Latest commit on origin/main: `39a0588` (Hermes prompt). 46 tests green (`pytest -m "not live"`).
- **Done & live:** spine, band layer, examples (demo_band + suno_band --grid), CI/Demo, LICENSE, CONTRIBUTING,
  SESSION-RECAP, build prompts, runbook, Hermes prompts.
- **Still NOT done:** (a) `CODE_OF_CONDUCT.md` — never landed; (b) `docs/runbook-cloud-rtx.md` exists but the
  in-engine bridge it points to is unbuilt; (c) `NvcfA2FTransport.process` (live A2F) is a stub;
  (d) `UnrealBandRenderTarget.open/push_vocal_frame` (the UE render bridge) is a stub.

## Verified facts — do NOT re-research
- A2F-3D `nvcr.io/nim/nvidia/audio2face-3d:2.0`: PCM mono 16k in; gRPC bidi `ProcessAudioStream`; ARKit-52
  + 10 emotions out (30/60 FPS); hosted free at `grpc.nvcf.nvidia.com:443` (key + function-id). SDK/UE plugin MIT.
- No audio→dance service. Dancing = librosa beats + clips retargeted in UE5. Render = Win + RTX, UE 5.6, ACE plugin 2.5.
- Suno data: Supabase `xltunldffphrlqstujyg`, `public.songs` (~1,459 rows). `audio_path` often a public
  `https://cdn1.suno.ai/<id>.mp3` URL (no key) — only sometimes a `personal-library` bucket path.

## Load-bearing gotchas (keep)
1. `Member.clips`/`Band.members` are tuples (Member is a hashable dict key). 2. `Band.vocalist` raises
ValueError if none. 3. `preflight()` is the CLI's job; `run()` never calls it; `open()` re-guards platform.
4. CLI → `click.ClickException` for NotImplementedError/config errors; `--engine` honors `RENDER_ENGINE`.
5. `get_track` passes through http(s) audio_path, signs bucket paths only. 6. ffmpeg-decode to WAV before
librosa. 7. `nvidia-ace` commented in pyproject; A2F transport stubbed until key+proto. 8. live tests gated by `@pytest.mark.live`.

## Next actions (in order)
1. Land `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1, contact davefurano@gmail.com) + links from README/CONTRIBUTING.
2. Implement `NvcfA2FTransport.process` against the pinned `nvidia-ace` proto (needs an `nvapi-` key) → green the live A2F test.
3. Implement the `UnrealBandRenderTarget` bridge on a Windows/RTX VM (see `docs/runbook-cloud-rtx.md`) → render the band to MP4.
   (Or hand 2+3 to specialist agents via `prompts/hermes-two-agents.prompt.md`.)

## Reusable prompts in this repo
- `prompts/avatar-house-band.prompt.md` — rebuild the pipeline fast (research pre-baked).
- `prompts/hermes-two-agents.prompt.md` — spawn ACE + Unreal specialist agents to finish the render path.
- `prompts/RESUME-how-we-got-here.prompt.md` — this file.
