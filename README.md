# Collegium OCR

OCR microservice that reads esports match scoreboards and returns per-player stats as
JSON. It is called by `collegium-server`'s `scanMatch` endpoint to pre-fill player KDA
when an organizer closes a tournament match, so an organizer can confirm or correct the
numbers instead of transcribing them by hand.

Valorant and League of Legends scoreboards are supported today. Call of Duty: Mobile
and Mobile Legends are not — see [Notes and known limitations](#notes-and-known-limitations).

The OCR reader is [RapidOCR](https://github.com/RapidAI/RapidOCR), running on the ONNX
Runtime. It executes on CPU by default and can be switched to GPU (CUDA) execution
without any code changes.

## Contents

- [Requirements](#requirements)
- [Project setup](#project-setup)
- [Running on CPU](#running-on-cpu)
- [Running on GPU](#running-on-gpu)
- [Configuration reference](#configuration-reference)
- [API](#api)
- [Tests](#tests)
- [Troubleshooting](#troubleshooting)
- [Notes and known limitations](#notes-and-known-limitations)

## Requirements

Two supported setups, depending on your OS. Both end up running the same
`pyproject.toml`/`uv.lock`-pinned dependency set through `uv` — pick the one that
matches your machine.

### Linux / macOS — with Nix

This is the reference setup and the one the maintainer develops against. The flake
provides a pinned Python 3.12 toolchain plus the native shared libraries RapidOCR's
OpenCV backend needs (`libGL`, `libX11`, `libxcb`, etc.), so nothing needs to be
installed on the host beyond Nix itself.

- [Nix](https://nixos.org/download) with flakes enabled
- `uv` — provided by the dev shell, no separate installation needed

### Windows (or any OS without Nix)

Most collaborators on this project are on Windows and do not have Nix installed —
this path is fully supported and does not require WSL. The native libraries the Nix
flake provides are a Linux concern (OpenCV's Windows wheel bundles its own DLLs), so
a plain Python install is sufficient.

- [Python 3.11 or 3.12](https://www.python.org/downloads/) (64-bit), added to `PATH`
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — install with:
  ```
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  (or `pip install uv` if you already have Python installed and prefer that)

### Both setups

- For GPU execution only: an NVIDIA GPU, a current NVIDIA driver, and a working
  CUDA userspace on the host (see [Running on GPU](#running-on-gpu)) — this applies
  identically whether you set up via Nix or via plain Windows Python.

## Project setup

Run these once after cloning the repository.

**Linux / macOS (Nix):**

```
nix develop
cp .env.example .env
uv sync
```

`nix develop` drops you into a shell with Python 3.12, `uv`, and the required native
libraries on `LD_LIBRARY_PATH`. Run every subsequent command from inside this shell.

**Windows (PowerShell, no Nix):**

```
copy .env.example .env
uv sync
```

There is no dev shell to enter — `uv sync` alone creates `.venv\` using your system
Python and installs everything from `uv.lock`. Run subsequent `uv run ...` commands
from a regular PowerShell or Command Prompt in the project directory; there is no
Nix-equivalent activation step.

**Either OS:**

- `cp`/`copy .env.example .env` creates your local environment file. The defaults
  (`USE_GPU=false`, `PORT=8000`) are correct for CPU-only development.
- `uv sync` installs the dependencies pinned in `uv.lock`. Re-run it any time
  `pyproject.toml` or `uv.lock` changes.

## Running on CPU

CPU execution is the default and requires no extra configuration. With `.env` present
and `uv sync` already run (inside `nix develop` on Linux/macOS, or a plain shell on
Windows — the command itself is identical either way):

```
uv run uvicorn app.main:app --reload --port 8000
```

- `--reload` restarts the server on source changes; drop it for a longer-lived local run.
- Confirm it is up:

```
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "ok", "gpu": false }
```

Interactive API documentation (Swagger UI) is served at `http://localhost:8000/docs`.

CPU execution is single-threaded per RapidOCR call and is adequate for interactive,
one-screenshot-at-a-time use from the organizer's close-match flow. It has no external
runtime dependencies beyond what `uv sync` installs, so it is the correct choice for
local development and for any deployment target without a GPU.

## Running on GPU

GPU execution uses the CUDA execution provider in ONNX Runtime and is opt-in. It is
worth enabling on a deployment host that processes scans continuously or under load;
it is not necessary for local development.

### GPU prerequisites

Verify these on the host before installing anything Python-side:

1. An NVIDIA GPU is present and visible:

   ```
   nvidia-smi
   ```

   This works identically on Linux and Windows once the driver is installed (`nvidia-smi`
   ships with the driver, not with CUDA). It must print your GPU and a driver version.
   If the command is not found or fails, install the NVIDIA driver first — no Python
   package in this project substitutes for the driver.

2. A CUDA and cuDNN runtime compatible with the installed `onnxruntime-gpu` version.
   `onnxruntime-gpu` does not bundle CUDA; it links against the CUDA and cuDNN shared
   libraries already present on the host. Because the required CUDA/cuDNN major
   versions change between `onnxruntime-gpu` releases, check the exact pairing for the
   version pinned in `uv.lock` against the
   [ONNX Runtime CUDA execution provider requirements](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
   before installing. Installing a mismatched CUDA/cuDNN pair is the single most
   common cause of GPU initialization failing silently at runtime.
   - On Linux, this is typically satisfied via the distribution's CUDA package or a
     `nvidia-*-cu12` pip wheel.
   - On Windows, install the matching [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
     and [cuDNN](https://developer.nvidia.com/cudnn) from NVIDIA directly (cuDNN on
     Windows is a manual DLL copy into the CUDA Toolkit directory, not an installer) —
     there is no pip-wheel shortcut on Windows the way there is on Linux.

### Installing the GPU extra

```
uv sync --extra gpu
```

This adds `onnxruntime-gpu` on top of the base dependency set. Both `onnxruntime`
(CPU) and `onnxruntime-gpu` install into the same `onnxruntime` Python package
namespace; see [Troubleshooting](#troubleshooting) if the service does not pick up
the GPU build after installing.

### Enabling GPU at runtime

Set in `.env`:

```
USE_GPU=true
```

Then start the service the same way as CPU:

```
uv run uvicorn app.main:app --reload --port 8000
```

Confirm it picked up the GPU:

```
curl http://localhost:8000/health
```

Expected response:

```json
{ "status": "ok", "gpu": true }
```

Note that `"gpu": true` here reflects the `USE_GPU` setting, not confirmed successful
CUDA initialization — `app/engine.py` attempts to construct the RapidOCR engine with
CUDA enabled and silently falls back to CPU execution if that construction raises
`TypeError`. If you need to confirm CUDA is actually being used (as opposed to a silent
CPU fallback), run the engine construction manually and watch for CUDA provider errors:

```
uv run python -c "
from app.engine import get_engine
get_engine()
"
```

Any CUDA/cuDNN loading error will surface here on stderr, even though `/health` would
still report `"gpu": true`.

### Reverting to CPU

Set `USE_GPU=false` in `.env` (or delete the line — it defaults to `false`) and restart
the process. No package changes are required to switch back.

## Configuration reference

All configuration is read from environment variables via `.env` (see `app/config.py`).

| Variable  | Default | Description                                                        |
| --------- | ------- | -------------------------------------------------------------------|
| `USE_GPU` | `false` | When `true`, attempts to construct the OCR engine with the CUDA execution provider. Falls back to CPU if construction fails. |
| `PORT`    | `8000`  | Informational; the actual bind port is set by the `uvicorn` `--port` flag, not read from this variable automatically. |

## API

### `GET /health`

Returns service status and the configured GPU flag. No parameters.

### `POST /ocr/scan`

Multipart form request.

| Field   | Type   | Required | Description                                              |
| ------- | ------ | -------- | --------------------------------------------------------- |
| `game`  | string | yes      | One of `VALORANT`, `LOL`, `CODM`, `MLBB` (case-insensitive). Only `VALORANT` and `LOL` currently return usable results — see [Notes and known limitations](#notes-and-known-limitations). |
| `image` | file   | yes      | The scoreboard screenshot. Must have an `image/*` content type. |

Example request (Linux/macOS shell, or Windows PowerShell — `curl` here resolves to
`curl.exe`, which accepts the same syntax):

```
curl -X POST http://localhost:8000/ocr/scan \
  -F "game=VALORANT" \
  -F "image=@scoreboard.png"
```

Example response:

```json
{
  "game": "VALORANT",
  "players": [
    {
      "ign": "NU Arguelles",
      "team": null,
      "kills": 18,
      "deaths": 13,
      "assists": 5,
      "extra": {}
    }
  ]
}
```

Error responses:

- `422` — `game` is missing or not one of the supported values
- `415` — `image` does not have an `image/*` content type
- `400` — `image` field was submitted empty
- `500` — the OCR engine or parser raised an exception; the response `detail` includes
  the underlying error message

## Tests

```
uv run pytest
```

Tests cover the per-game text parsers (`tests/test_parsers.py`) against fixed OCR
output samples. They do not exercise the OCR engine itself and do not require a GPU.

## Troubleshooting

**`ImportError` / shared library errors on startup (e.g. `libGL.so.1: cannot open
shared object file`) — Linux/macOS (Nix) only**
You are not inside the Nix dev shell, or `LD_LIBRARY_PATH` was not exported. Re-enter
with `nix develop` and re-run the server from that shell. This class of error does not
apply on Windows — OpenCV's Windows wheel is self-contained.

**`uv : File ... cannot be loaded because running scripts is disabled on this system`
(Windows)**
PowerShell's execution policy is blocking the `uv` installer script or a generated
activation script. Either run the installer with
`powershell -ExecutionPolicy ByPass -c "..."` as shown above, or install `uv` via
`pip install uv` instead, which does not require a PowerShell script to run.

**Health check reports `"gpu": true` but scans are slow / CPU-bound**
`get_engine()` fell back to CPU because RapidOCR could not initialize the CUDA
provider. This happens most often when the installed CUDA/cuDNN runtime does not match
what `onnxruntime-gpu` expects, or when both `onnxruntime` and `onnxruntime-gpu` are
installed and the wrong one's shared libraries were picked up. Run the manual engine
construction command from [Running on GPU](#running-on-gpu) to see the underlying
error, and confirm `nvidia-smi` succeeds on the host.

**GPU install seems to have no effect after `uv sync --extra gpu`**
Because `onnxruntime` (CPU, pulled in transitively by `rapidocr-onnxruntime`) and
`onnxruntime-gpu` both occupy the same `onnxruntime` import path, installation order
in the virtual environment can leave the CPU build's files in place. Force a clean
reinstall of the GPU package after syncing:

```
uv sync --extra gpu --reinstall-package onnxruntime-gpu
```

**`422 Unsupported game` on a request you believe is correctly formed**
The `game` field is matched case-insensitively against exactly
`VALORANT`, `LOL`, `CODM`, `MLBB` — check for a typo or an extra whitespace character
in the form field.

## Notes and known limitations

- Only Valorant and League of Legends are supported end to end today, in both this
  service and the `collegium-web` close-match screen it feeds. Call of Duty: Mobile
  and Mobile Legends are not yet ready:
  - Mobile Legends (`MLBB`) packs kills, deaths, assists, and gold with no separators
    in its scoreboard layout, so those numbers are not reliably parsed. MLBB scans
    currently return no players; organizers enter those stats manually.
  - Call of Duty: Mobile (`CODM`) is accepted by the API but has not been validated
    against real CODM scoreboard layouts — treat it as unsupported for now, not as a
    working integration.
  Both are left for a later iteration; this is a known gap, not a bug.
- The OCR engine instance is cached process-wide (`lru_cache(maxsize=1)` in
  `app/engine.py`) and is constructed lazily on the first scan request, not at process
  startup — the first request after a cold start will be slower than subsequent ones.
