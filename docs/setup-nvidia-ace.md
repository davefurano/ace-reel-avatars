# Setup: NVIDIA Audio2Face-3D

> This covers both the hosted endpoint (iterates on any machine, including the Mac) and the self-hosted path (requires a 24 GB NVIDIA GPU).

## 1. Get an API key

1. Go to [build.nvidia.com](https://build.nvidia.com) and sign in with an NVIDIA developer account.
2. Navigate to **Audio2Face-3D** in the model catalog.
3. Click **Get API Key**. The key begins with `nvapi-`.
4. Copy it into your `.env` file as `NVIDIA_API_KEY=nvapi-...`.

## 2. Hosted endpoint (no GPU)

The hosted endpoint is `grpc.nvcf.nvidia.com:443`. Each model has a **function-id** — a UUID that identifies the specific model variant you want to call. You must include both the API key and the function-id in gRPC metadata on every request.

### Per-model function-ids

Function-ids are shown on each model's page at build.nvidia.com after you log in. The three available models in the A2F-3D 2.0 release are:

| Model | Notes |
|---|---|
| `james_v2.3.1` | Default. Male voice profile. 30 FPS regression mode. |
| `claire_v2.3.1` | Female voice profile. 30 FPS regression mode. |
| `mark_v2.3` | Additional male profile. 30 FPS regression mode. |
| `multi_v3.2` | Diffusion mode. 60 FPS. Higher latency. |

Set the chosen function-id in your `.env`:

```bash
A2F_GRPC_ENDPOINT=grpc.nvcf.nvidia.com:443
A2F_FUNCTION_ID=<paste-function-id-from-build.nvidia.com>
```

### Required audio format

A2F-3D accepts **PCM mono, 16-bit signed, 16 kHz only**. The orchestrator transcodes from the source file automatically via ffmpeg (`to_pcm_16k_mono_bytes` in `src/ace_reel/orchestrator.py`). ffmpeg must be on `PATH`.

### gRPC protocol

A2F-3D 2.0 uses **bidirectional streaming only** via the `ProcessAudioStream` RPC. The legacy unidirectional endpoints from v1 are removed. The stream sends an audio header (format + sample-rate) followed by audio chunks; the server returns `AnimationDataStream` messages containing per-frame blendshape weights and emotion values.

## 3. The `nvidia-ace` Python package

The `nvidia-ace` package exposes the gRPC stubs (`ProcessAudioStream`, `AnimationDataStream`, `SkelAnimationHeader`) needed to implement `NvcfA2FTransport.process`. It is listed in `pyproject.toml` but currently **commented out** because it failed to install in the initial build environment:

```toml
# nvidia-ace>=1.2,  # TODO: re-pin in Task 4 (fails to install in this environment)
```

**Before implementing `NvcfA2FTransport.process`:**

1. Confirm the current installable version:
   ```
   pip index versions nvidia-ace
   ```
2. Install and verify the proto stubs are present:
   ```
   pip install nvidia-ace
   python -c "from nvidia.ace.audio2face.v1_pb2 import AudioStream; print('OK')"
   ```
3. Un-comment and pin the version in `pyproject.toml`:
   ```toml
   "nvidia-ace==<confirmed-version>",
   ```
4. Implement `NvcfA2FTransport.process` in `src/ace_reel/ace/ace_client.py` using the confirmed stubs and the `ProcessAudioStream` protocol documented at [docs.nvidia.com/ace/audio2face-3d-microservice](https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/interacting/a2f-rpc.html).

The `NvcfA2FTransport` docstring in `ace_client.py` captures the verified wiring from Phase 0.

## 4. Self-hosted A2F-3D (optional)

Pull and run the NIM container:

```bash
docker run --gpus all -p 8000:8000 -p 52000:52000 \
  nvcr.io/nim/nvidia/audio2face-3d:2.0
```

Minimum GPU: one 24 GB RTX card (RTX 4090, 5080, 5090, or 6000 Ada) or an L4/L40S/A10G in a cloud instance. A100/H100 requires a local TensorRT profile build (not provided by default).

Health check: `curl http://localhost:8000/v1/health/ready`

Point the endpoint at the local container:

```bash
A2F_GRPC_ENDPOINT=localhost:52000
```

The API key is still required for the hosted function-id routing; for local containers, the key requirement depends on your NIM configuration.

## 5. Running the live AceClient test

The `@live`-marked test in `tests/test_ace_client.py` hits the hosted endpoint and requires a real key:

```bash
source .env   # or export vars manually
NVIDIA_API_KEY=nvapi-... A2F_FUNCTION_ID=<uuid> \
  python -m pytest tests/test_ace_client.py -v -m live
```

The test expects a short WAV file at `tests/data/sample_vocal.wav` (any royalty-free vocal clip, minimum ~2 seconds). Create that directory and drop in a file before running.

Without an API key the test is automatically skipped:

```
pytest -m "not live"   # runs all 24 non-live tests; no key needed
```

## 6. Licensing

- Models (`claire_v2.3.1`, `james_v2.3.1`, `mark_v2.3`, `multi_v3.2`): open weights under the NVIDIA Open Model License (hosted on Hugging Face).
- SDK + UE plugin: MIT.
- NIM container (`nvcr.io/nim/nvidia/audio2face-3d:2.0`): NVIDIA AI Enterprise license (free for development/evaluation).
