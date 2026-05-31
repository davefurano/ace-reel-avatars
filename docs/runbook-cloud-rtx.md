# Runbook — Watch the Avatar House Band on a cloud RTX VM

The Mac produces the performance data (tempo → per-player beat grid + the vocalist's lip-sync stream).
**Rendering the MetaHumans is GPU work** and only runs on **Windows + an NVIDIA RTX/data-center GPU**.
This runbook stands up that machine, renders, and gets you a video you can watch anywhere.

## 1. Rent a Windows GPU VM (hourly)
Any of these has a GPU the ACE plugin supports (Ampere/Ada/Blackwell):

| Provider | Instance | GPU | ~$/hr |
|---|---|---|---|
| AWS EC2 | `g5.2xlarge`, Windows Server 2022 | A10G (24 GB) | ~1.20 |
| Azure | NVadsA10 v5, Windows | A10 | ~1.00 |
| GCP | G2 + L4, Windows | L4 | ~0.70 |
| Paperspace | RTX A4000/A5000 (Windows) | RTX | ~0.75 |

Pick **hourly billing** and stop the VM when idle. 24 GB VRAM is comfortable; the A2F profiles cover
A10G/L4/L40S/RTX 4090/5080/5090/6000 Ada.

## 2. Connect (use a 3D-friendly client, not bare RDP)
Install **Parsec** or **NICE DCV** on the VM and connect with it — plain RDP is laggy for real-time 3D.
This is your "screen" to watch the band live.

## 3. Install the stack (one-time, ~1–2 hrs)
1. **NVIDIA driver 551.78+** (552+ recommended).
2. **Unreal Engine 5.6** via the Epic Games Launcher (free).
3. **NVIDIA ACE Unreal plugin 2.5** — `NV_ACE_Reference` from developer.nvidia.com / Fab. Add the
   local-inference model plugins only if you want self-hosted A2F; otherwise use the hosted endpoint.
4. **NVIDIA API key** (free) from build.nvidia.com → set `NVIDIA_API_KEY` + the A2F `function-id`.

## 4. Build the scene (see `docs/setup-reel-engine.md` for the detailed wiring)
- Import the 5 MetaHumans named in `bands/house.json` (Claire/Mark/James/Beat/Rhodes).
- **Vocalist face:** add `Apply ACE Face Animations` to the MetaHuman `Face_AnimBP` before
  `mh_arkit_mapping_pose` (swap to NVIDIA's `mh_arkit_mapping_pose_A2F`); provider = RemoteA2F (gRPC,
  hosted). Audio + animation arrive co-synced.
- **Instrumentalists:** retarget instrument/idle motion clips onto `metahuman_base_skel` via the IK
  Retargeter, scheduled from each member's `ClipCue` timeline (the `X . X .` grid the pipeline emits;
  `start_s` = when, `energy` = playback rate/amplitude). Layered Blend Per Bone (mask from
  `spine_03`/`neck_01`) keeps face + body independent.
- **Bridge:** implement `UnrealBandRenderTarget.open/push_vocal_frame` (currently stubs) against a small
  in-engine receiver — see `src/ace_reel/render/unreal_band.py` for the protocol contract and
  `docs/setup-reel-engine.md` for the engine side. This is the remaining engineering before anything renders.

## 5. Watch / export
- **Live:** Play-in-Editor (PIE) and watch over Parsec.
- **Video (recommended to share):** Sequencer → **Movie Render Queue**, output **1080×1920** MP4.
  Download the file — then it plays on any device with no GPU. The VM is only needed to *produce* it.

## Cost / time reality
- VM: ~$1–3/hr, only while on.
- One-time setup + the bridge implementation: a few hours of engineering, not one-click.
- Driving the band from this repo: run the Mac-side orchestrator (`band-perform`/`suno_band.py`) to
  stream frames + cue timelines to the in-engine bridge once it's implemented.

## Quick-look alternative (no full render)
To *preview* lip-sync without UE at all: upload a vocal clip to the Audio2Face-3D playground at
build.nvidia.com/nvidia/audio2face-3d — you'll see one generic head lip-sync. It is face-only and not
your band, but it confirms the A2F path end to end.
