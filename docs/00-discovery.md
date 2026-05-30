# Phase 0 — Discovery Findings

> NVIDIA ACE × Unreal Engine 5 singing/dancing avatar pipeline, fed by the AImyMusic Suno library.
> Date: 2026-05-30. Every claim below is grounded in current docs (URLs inline). Where this
> contradicts the build prompt, **the live docs win** and the deviation is noted.

## TL;DR — the two findings that reshape the build

1. **NVIDIA ACE has NO turnkey audio→body/dance service.** ACE is **face-only**: Audio2Face-3D
   emits ARKit-52 blendshapes + 10 emotion channels, and nothing else. The only body offering
   NVIDIA ever shipped, **Audio2Gesture**, was co-speech *upper-body gesture* (never full-body
   dance), was an Omniverse extension (never a NIM), and is **discontinued** (Omniverse Launcher
   deprecated 2025-10-01; "available soon" on marketing pages for ~2 years = vaporware).
   → **Dancing must use the prompt's fallback path:** beat/tempo detection (librosa/aubio, since
   the `songs` table has no BPM column) driving a **curated dance motion-clip library** retargeted
   onto the MetaHuman body via UE5's **IK Retargeter**, then layered-blended with the ACE face.

2. **None of the render/inference stack runs on this MacBook Air.** The ACE Unreal plugin 2.5
   support matrix is **Win64 or Linux only — macOS is entirely unlisted**, and local A2F inference
   is **Windows + NVIDIA RTX (Ampere/Ada/Blackwell) only**. The Mac can serve as a **thin Python
   orchestration terminal** talking gRPC to the **hosted** A2F endpoint on build.nvidia.com — but
   it cannot host UE5, MetaHuman, or the engine bridge. **Phases 3–6 require a Windows/RTX box.**

---

## A. NVIDIA ACE inventory

### Audio2Face-3D (A2F-3D) — the singing lip-sync core ✅ use it
- **Container:** `nvcr.io/nim/nvidia/audio2face-3d:2.0` (NGC). Models: `claire_v2.3.1`,
  `james_v2.3.1` (default), `mark_v2.3` (regression) + `multi_v3.2` (diffusion).
  — https://docs.nvidia.com/ace/audio2face-3d-microservice/2.0/text/support-matrix.html
- **Input:** PCM **mono, 16-bit, 16 kHz**. **Protocol:** gRPC **bidirectional streaming only**
  (`ProcessAudioStream`); legacy unidirectional endpoints removed in v2.0. Health on HTTP :8000.
  — https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/interacting/a2f-rpc.html
- **Output:** `AnimationDataStream` = **ARKit-52 blendshapes** (+ extra tongue shapes) + per-frame
  timecodes + **10 emotion channels** (`amazement, anger, cheekiness, disgust, fear, grief, joy,
  outofbreath, pain, sadness`, 0–1). **30 FPS** (regression) / **60 FPS** (diffusion).
- **Hosted free endpoint (no GPU):** `grpc.nvcf.nvidia.com:443` via build.nvidia.com + API key +
  per-model function-id. **This is our Mac-friendly iteration path.**
  — https://build.nvidia.com/nvidia/audio2face-3d/api
- **Self-host GPU:** single 24 GB RTX (4090/5080/5090/6000 Ada), or L4/L40S/A10G (pre-built TRT
  profiles). A100/H100 need local TRT build.
- **Licensing:** models = open weights (NVIDIA Open Model license, on HF); **SDK + Maya/UE5
  plugins = MIT**; NIM container = NVIDIA AI Enterprise (free for dev/eval).
  — https://github.com/NVIDIA/Audio2Face-3D

### Audio2Emotion — folded into A2F-3D
Emotion is built into the A2F-3D NIM: auto-detected from audio, **or** supplied directly as
time-coded values. **For singing, drive the 10 channels manually per song section** (sung vocals
confuse audio-based tone detection).

### Body / dance from audio — ❌ does not exist (see TL;DR #1)
Use the **beat-synced motion-clip fallback**. ACE contributes face only.

### ACE Animation Graph / Pipeline — skip for UE5
Omniverse-renderer-centric. The "Animation Pipeline" reference workflow is **deprecated**. For a
UE5/MetaHuman renderer you **bypass it** and blend face+body inside UE's own AnimGraph.
— https://docs.nvidia.com/ace/animation-graph-microservice/latest/index.html

### ACE Controller (Pipecat) — skip for v1
Now `NVIDIA/voice-agent-examples` v0.4.0 (BSD-2-Clause). Its value is the conversational
ASR→LLM→TTS→A2F chain — **dead weight** when feeding recorded vocals. Write a **thin custom
orchestrator** (WAV → A2F gRPC → frames → render target). Adopt ACE Controller only if we later
add interactivity. **Riva (ASR/TTS) = out of scope** for real-vocal singing.

---

## B. Unreal Engine target

### ACE Unreal Engine plugin — v2.5
- Supports **UE 5.5 / 5.6**, **Win64 / Linux only**. Base plugin `NV_ACE_Reference` from
  developer.nvidia.com / Fab; local-inference model plugins (`NvAudio2FaceClaire/James/Mark`) ship
  alongside. — https://docs.nvidia.com/ace/ace-unreal-plugin/2.5/ace-unreal-plugin-install.html
- **NOT Live Link** (deprecated since plugin 2.0.0). Animation enters via the Anim Blueprint node
  **`Apply ACE Face Animations`**, wired into the MetaHuman `Face_AnimBP` before the
  `mh_arkit_mapping_pose` node. Two providers: **RemoteA2F** (gRPC to NVCF/self-hosted) or
  **Animation Stream** (subscribe to NVIDIA Animgraph). Audio + animation arrive **co-synced**
  (manual offset removed in 2.0.0). — https://docs.nvidia.com/ace/ace-unreal-plugin/2.5/ace-unreal-plugin-audio2face.html

### MetaHuman (2026)
- Left Early Access (June 2025), now **part of UE 5.6**, **free under standard UE license**,
  tradeable on Fab, exportable to other engines. — https://www.metahuman.com/license
- **ARKit→MetaHuman remap is built in:** Epic's `mh_arkit_mapping_pose` PoseAsset; NVIDIA ships a
  tuned `mh_arkit_mapping_pose_A2F` variant (adjusts 5 curves). **No custom remapper needed.**

### Body / dancing in UE5
- MetaHuman body rides `metahuman_base_skel`. Retarget Mixamo/mocap dance clips via **IK Rig + IK
  Retargeter** (`RTG_<src>_metahuman_base_skel`). Blend face+body with **Layered Blend Per Bone**
  masking from `spine_03`/`neck_01`. — https://dev.epicgames.com/documentation/en-us/metahuman/

### Reel export
- **Sequencer → Movie Render Queue / Movie Render Graph**; portrait output (e.g. 1080×1920) is just
  a custom resolution. Bake ACE curves to an Anim Sequence and render offline (no live streaming
  needed). UE 5.5 has a Sound Wave "Force Inline" crash — prefer **5.6**.

### Hardware/OS — hard blocker
**Win64/Linux + NVIDIA RTX (Ampere/Ada/Blackwell), driver 551.78+.** No macOS. Minimum real setup:
**Windows 10/11 + NVIDIA RTX 30/40/50-series + UE 5.6 + ACE plugin 2.5.**

---

## C. AImyMusic Suno library — data layer

> ⚠️ **Discrepancy to resolve:** the `aimymusicapp` repo (where this prompt lives) links to Supabase
> project `buxczmwjtolablzibuib` (no MCP access). The **real Suno library** is in the canonical
> **aimy monorepo** project `xltunldffphrlqstujyg` (`ai-my-service-network`). Confirm which is the
> source of truth before wiring `MusicSource`.

- **Table `public.songs` — 1,459 rows** (prompt said ~472; live count is larger). Key columns:
  `id` (text), `suno_id` (uuid), `title`, `styles` (text[]), `lyrics`, **`duration_seconds`** (int),
  `audio_path` (text), `cover_path`, `video_path`, `suno_url`, `visibility`, `owner_rating`,
  `tags` (text[]), `content_hash`. Supporting: `song_ratings` (110), `track_overrides` (30),
  `suno_trash_queue`, and the `soundtrack` app (`AImySoundtrack`).
- **Audio fetch:** `audio_path` → signed URL from storage bucket **`personal-library`** (1,905
  objects = audio/cover/video). A2F needs PCM mono 16 kHz, so the source (mp3/m4a) must be
  **transcoded** (ffmpeg) before streaming to A2F.
- **No BPM/tempo column** → derive tempo with librosa/aubio for the dance beat-sync (Phase 4).
- **No vocal stem** stored → feed the **full mix** to A2F v1 (note quality tradeoff; stem
  separation, e.g. Demucs, is a future upgrade).
- **Auth/billing:** reuse the monorepo's wallet/Stripe + RLS patterns (`wallet_balances`,
  `wallet_transactions`, profiles/subscriptions). A performance run is a billable operation.

---

## Recommended path (pending Dave's go-ahead)

- **Renderer:** UE 5.6 + MetaHuman + ACE plugin 2.5 on a Windows/RTX box. Mac = orchestration only.
- **Face:** A2F-3D, hosted NVCF endpoint for iteration; emotion driven manually per section.
- **Body/dance:** beat-synced curated motion-clip library retargeted via UE5 IK Retargeter
  (NVIDIA ships no audio→dance). Optional future: third-party music-to-motion model (EDGE-class).
- **Music:** `AImyMusicSunoSource` over the `songs` table + `personal-library` bucket, with an
  ffmpeg transcode step to 16 kHz mono PCM.
- **Orchestrator:** thin custom Python (skip ACE Controller/Riva).
- **What's buildable + verifiable on the Mac now:** the engine-agnostic template spine —
  `contracts/` (AnimationFrame), `AceClient` (verifiable against hosted A2F), `MusicSource`,
  `orchestrator`, beat-detection module, contract tests. `UnrealLiveLinkTarget` can be written but
  only **verified on Windows/RTX**.
