# Setup: Reel Engine (Windows/RTX)

> **Every step in this document requires Windows 10/11 + an NVIDIA RTX GPU (Ampere, Ada Lovelace, or Blackwell generation). None of this runs on macOS.** The MacBook Air runs the Python spine and the hosted A2F gRPC client; it does not run Unreal Engine 5, the ACE plugin, or MetaHuman.

## Hardware requirements

- OS: Windows 10 or Windows 11 (64-bit)
- GPU: NVIDIA RTX 30-series, 40-series, or 50-series with current Game Ready or Studio driver (551.78+)
- UE 5.6 storage: ~50 GB
- ACE plugin 2.5: ~2 GB additional

## 1. Install Unreal Engine 5.6 (Windows/RTX only)

1. Download and run the Epic Games Launcher from [unrealengine.com](https://www.unrealengine.com).
2. In the launcher, go to **Unreal Engine** → **Library** and install **UE 5.6**.
3. Prefer 5.6 over 5.5. UE 5.5 has a known Sound Wave "Force Inline" crash that affects reel export with audio.

## 2. Install the ACE Unreal Plugin 2.5 (Windows/RTX only)

The base plugin is `NV_ACE_Reference`, distributed at [developer.nvidia.com](https://developer.nvidia.com) and on Fab.

1. Download **ACE Unreal Engine Plugin 2.5** from the NVIDIA developer portal.
2. Unzip into your UE project's `Plugins/` directory: `<YourProject>/Plugins/NV_ACE_Reference/`.
3. Launch your UE project. UE will prompt to build the plugin — allow it (requires Visual Studio 2022 with C++ workload).
4. Enable the plugin in **Edit → Plugins → NVIDIA ACE** if it is not already enabled.

**Note:** The plugin supports Win64 and Linux. macOS is not listed in the support matrix. The Live Link integration was deprecated in plugin version 2.0.0 and is not used here.

## 3. Import a MetaHuman (Windows/RTX only)

MetaHuman is part of UE 5.6 and is free under the standard UE license.

1. In UE 5.6, open **Quixel Bridge** (via the toolbar or Window menu).
2. Select or create a MetaHuman character. Download to your project.
3. The MetaHuman body skeleton is `metahuman_base_skel`. The face animation target is `Face_AnimBP`.

## 4. Wire ACE face animations into the MetaHuman AnimGraph (Windows/RTX only)

The ACE plugin provides an Anim Blueprint node called **Apply ACE Face Animations**. This node must be placed in the MetaHuman's `Face_AnimBP` before the ARKit mapping node.

Steps:

1. Open the MetaHuman `Face_AnimBP` in UE.
2. In the AnimGraph, find the existing `mh_arkit_mapping_pose` node.
3. **Replace** `mh_arkit_mapping_pose` with the NVIDIA-tuned variant: `mh_arkit_mapping_pose_A2F`. NVIDIA ships this adjusted pose asset alongside the plugin (it corrects 5 blendshape curves relative to Epic's default mapping).
4. Add the **Apply ACE Face Animations** node upstream of `mh_arkit_mapping_pose_A2F`.
5. Set the provider to **RemoteA2F** (gRPC). Configure the endpoint to point at the hosted A2F endpoint (`grpc.nvcf.nvidia.com:443`) or your self-hosted container. Provide the API key and function-id.
6. Compile and save the AnimBP.

Audio and animation arrive co-synced through the RemoteA2F provider. Manual audio-animation offset (required before plugin 2.0.0) is no longer needed.

## 5. Retarget dance clips for the MetaHuman body (Windows/RTX only)

NVIDIA provides no audio-to-dance service. Dance clips (Mixamo, mocap, or other sources) must be retargeted onto `metahuman_base_skel` using UE5's IK tools.

1. **Create an IK Rig** for the source skeleton (e.g., Mixamo's `mixamorig:Hips` hierarchy).
2. **Create an IK Rig** for `metahuman_base_skel`.
3. **Create an IK Retargeter** (`RTG_<source>_metahuman_base_skel`) linking the two IK Rigs.
4. In the IK Retargeter, preview and adjust chain mappings until the clip looks correct on the MetaHuman body.
5. Export the retargeted animations into your project's content folder.

## 6. Blend face and body animations (Windows/RTX only)

Face (from ACE) and body (from dance clips) are combined in the MetaHuman's body `AnimBP` using a **Layered Blend Per Bone** node.

- Body input: the retargeted dance clip animation.
- Face/upper-body override input: the ACE face animation output from `Face_AnimBP`.
- Blend mask: start the face/upper blend from `spine_03` or `neck_01` so the face layer does not corrupt leg/foot poses.

The `ClipCue` timeline produced by `src/ace_reel/motion/planner.py` tells the engine which clip to play at which timestamp and at what energy level. Wire these values into UE's Sequencer or a Blueprint that reads the cue list at runtime.

## 7. Export the reel via Movie Render Queue (Windows/RTX only)

1. Set up a **Level Sequence** in UE containing the MetaHuman actor, the audio track, and the ACE face curve data (baked to an Anim Sequence).
2. Open **Movie Render Queue** (Window → Cinematics → Movie Render Queue).
3. Add a new job pointing at your Level Sequence.
4. In job settings, set **Output Resolution** to a custom size: `1080 × 1920` (portrait). UE accepts any resolution here.
5. Add an **Apple ProRes** or **EXR Sequence** output pass as needed.
6. Click **Render (Local)**.

For higher quality, use the **Movie Render Graph** (UE 5.6 feature) to add anti-aliasing samples or temporal accumulation passes.

## 8. What the Python spine does not do

The Python package (`src/ace_reel/`) handles:
- Fetching audio from the Supabase `songs` table + `personal-library` bucket
- Transcoding audio to PCM mono 16 kHz (ffmpeg)
- Streaming audio to the hosted A2F-3D gRPC endpoint
- Receiving `AnimationFrame`s (ARKit-52 blendshapes + emotions)
- Beat detection and generating the `ClipCue` dance timeline

Everything in this document — UE 5.6, MetaHuman, ACE plugin, IK retarget, Sequencer, render — happens inside Unreal Engine on a Windows/RTX machine.

The `UnrealRenderTarget` class in `src/ace_reel/render/unreal_livelink.py` is a conforming stub. It implements the `RenderTarget` interface and its `open()` raises `NotImplementedError` with a clear message when called outside Windows. Completing the in-engine bridge (forwarding `AnimationFrame`s from Python to a running UE5 instance) is a Phase 3 task that requires this Windows/RTX setup.
