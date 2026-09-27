# Local image-to-3D feasibility — read-only assessment

**Best first bounded trial: TripoSR, in an isolated native-Windows Python3.10 environment.** It is the smallest of the reviewed options with a permissive model license and an official approximately6GB single-image VRAM baseline. This is a feasibility recommendation, not a claim that inference has run or that its output will meet the locked concept. No model, runtime or dependency was installed in this assessment.

## Current machine observations

- NVIDIA GeForce RTX3070 Laptop GPU,8192MiB VRAM, driver581.80. The observed snapshot had2252MiB used and5769MiB free; free VRAM changes with Unity/Blender activity.
- Windows reports68,478,226,432 bytes of physical memory, approximately63.78GiB usable from64GiB installed.
- Only Python3.13.12 was discovered by the Windows launcher and `uv python list --only-installed`. Global Python has no PyTorch, torchvision, diffusers, transformers or huggingface_hub. NumPy and rembg are present, but would not be modified.
- `nvcc`, `cmake`, `ninja` and `cl` are not on PATH. `CUDA_PATH` is unset and no toolkit was found at the standard NVIDIA toolkit directory. Visual Studio18 Enterprise reports the C++ tools component installed. Its optional bundled CMake/Ninja paths were not present. This does not prove no private portable toolkit exists elsewhere.
- WSL has only a stopped `docker-desktop` distribution; there is no user Ubuntu development distro to reuse.
- `uv` and Git are available. Observed free space: D:358,700,163,072 bytes, C:63,321,092,096 bytes. A trial should remain on D: inside `_local/p08-local3d/`.

## Three reviewed candidates

| Candidate | Concrete model download | Hardware/software evidence | Decision |
|---|---:|---|---|
| TripoSR | `model.ckpt`1,677,246,742 bytes plus987-byte config; DINO tokenizer additionally requests only its small config, not another encoder checkpoint | Official README reports approximately6GB VRAM for one image. CLI has chunk-size control, CPU fallback, OBJ/GLB output and optional texture baking. Source and weights are MIT. | Best first trial; current free VRAM is tight, so coordinate with rendering work or start conservatively with chunk2048 and grid128. |
| TripoSG | Three safetensor components total7,946,488,460 bytes; complete listed repository7,946,494,238 bytes | Repo says at least8GB; model card says greater than8GB. Default script loads the pipeline and background model onto CUDA. Old NumPy1.22.3 pin targets Python3.10; `diso` adds native/CUDA setup risk. | Better shape-model candidate for later investigation, but less reliable as the first8GB Windows trial. Its default BRIA dependency must be removed/replaced for this free commercial workflow. |
| Hunyuan3D-2mini Turbo | Selected DiT+VAE safetensors4,229,994,604 bytes; do not download the entire25.26GB multi-variant listing | Official family README states6GB for shape,16GB for shape+texture; mini offers low-VRAM mode. | Do not select for this worldwide game: the current license excludes EU/UK/South Korea and its output-use clause also has territorial restrictions. |

Sources: [TripoSR official repository and MIT scope](https://github.com/VAST-AI-Research/TripoSR), [TripoSR inference options](https://github.com/VAST-AI-Research/TripoSR/blob/main/run.py), [TripoSR tokenizer](https://github.com/VAST-AI-Research/TripoSR/blob/main/tsr/models/tokenizers/image.py), [TripoSG official repository](https://github.com/VAST-AI-Research/TripoSG), [TripoSG model card](https://huggingface.co/VAST-AI/TripoSG), [Hunyuan official resource requirements](https://github.com/Tencent-Hunyuan/Hunyuan3D-2#-models-zoo), [Hunyuan license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE). Model byte counts came from the publishers' public Hugging Face tree APIs, not estimated parameter counts.

The TripoSG code and weights are MIT, but its default script unconditionally downloads `briaai/RMBG-1.4`. That model is available without a fee only for noncommercial use; a commercial agreement is required otherwise. TripoSG's image preparation can accept a valid existing alpha channel, so an audited local runner could avoid loading BRIA and use an already approved cutout. This requires an explicit local adaptation; the stock command is not suitable unchanged. [Default inference source](https://github.com/VAST-AI-Research/TripoSG/blob/main/scripts/inference_triposg.py), [alpha-input handling](https://github.com/VAST-AI-Research/TripoSG/blob/main/scripts/image_process.py), [BRIA model license statement](https://huggingface.co/briaai/RMBG-1.4).

## Practical TripoSR setup boundary

The existing Python3.13 environment is not a suitable target for the original pinned dependencies. PyPI metadata confirms Windows CPython3.10 wheels for Pillow10.1.0 and xatlas0.0.9; the same versions do not list CPython3.13 Windows wheels. Keep a project-local managed Python3.10 and virtual environment rather than changing global Python or Unity/Blender dependencies. [Official dependency list](https://github.com/VAST-AI-Research/TripoSR/blob/main/requirements.txt).

The main complication is `torchmcubes`: the requirements install it from source, and no public PyPI project was found. Its CMake file detects CUDA and links the Torch CMake package; without the local toolkit, a CUDA build is unavailable and even a CPU-extension build with a CUDA Torch wheel needs verification. The official TripoSR helper already handles a CPU marching-cubes fallback. For a narrowly bounded trial, the simpler adaptation is a reviewed CPU `scikit-image.measure.marching_cubes` adapter that preserves the helper's coordinate order, isolevel and face winding, verified with an asymmetric synthetic volume first. This avoids installing a CUDA toolkit or changing global build tools. It is a proposal, not a tested patch. [Official marching-cubes helper](https://github.com/VAST-AI-Research/TripoSR/blob/main/tsr/models/isosurface.py), [native extension build configuration](https://github.com/tatsy/torchmcubes/blob/master/CMakeLists.txt).

For a conservative environment baseline, direct official Windows wheel HEAD requests returned2,449,372,784 bytes for Torch2.5.1+cu121 CPython3.10 and6,063,665 bytes for torchvision0.20.1+cu121. These plus the model account for4,132,683,191 bytes before Python and other packages. Allow approximately4.5–6GB total downloads and reserve15GB local disk including caches; these totals are planning estimates, not an installed-footprint measurement. Download only required model files, not example videos or unused variants. CUDA inference wheels include their runtime; a separate system CUDA toolkit should not be needed if the native marching-cubes extension is avoided.

Do not blindly install the unbounded Gradio/UI dependency chain for a one-image CLI trial. Pin compatible packages in the isolated environment. The checkpoint loader should explicitly use `torch.load(..., weights_only=True)` and reject unsupported payloads rather than silently falling back to unrestricted pickle loading. Code/model hashes should be recorded. The official loader currently calls `torch.load` without that explicit flag. [Loader source](https://github.com/VAST-AI-Research/TripoSR/blob/main/tsr/system.py).

## Proposed bounded trial, after root authorization

1. One isolated directory `_local/p08-local3d/` containing the managed Python, virtual environment, reviewed/pinned official source and model cache. No global package/toolchain changes, no new WSL distro, no paid service, no Blender addon installation.
2. One derived single-view input from the already locked concept, with source hash and exact crop/mask provenance. Preserve the original concept unchanged. A multi-view contact sheet must not be fed as if it were a single object photograph.
3. First run: one mesh, grid128, chunk2048, no render video and no texture-bake dependency until shape usefulness is known. Record actual VRAM peak, duration and output hash. A grid256 comparison is justified only if the first run improves the forms and fits the measured budget.
4. Keep caches under the task directory; disable implicit Hugging Face credentials and telemetry; switch to offline model loading after required files are available. No concept image is sent to a service.
5. Import the OBJ/GLB through the existing direct Blender MCP for comparison with the locked view and other concept views. It remains an unaccepted starting mesh until anatomy/mechanical geometry, retopology, PBR maps, rig, LODs and native Unity checks pass.

Single-view reconstruction cannot establish unseen-side accuracy or100% concept fidelity. In particular, a smooth textured resemblance may hide wrong hands, garment structure, wheels, forks or openings. The bounded trial is useful only if it gives a better editable starting surface than the current procedural hero models.

## Observed pins

- TripoSR source: `107cefdc244c39106fa830359024f6a2f1c78871`.
- TripoSR model: `5b521936b01fbe1890f6f9baed0254ab6351c04a`, public, ungated, MIT metadata.
- TripoSG source: `fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c`.
- TripoSG model: `2c1c516d22d58db486a058d98d31bb6177344e06`, public, ungated, MIT metadata.
- Hunyuan mini model: `f90a0f7df7d5e6f71109cf333f6a95a0ae3194a6`, public, ungated, custom license.
- torchmcubes source inspected: `879926d0ef58e6ce0ac2630fdecb5e53af7ed3ff`.

These are read-only observations on2026-09-27. No runnable local inference, quality improvement or production acceptance is claimed yet.

## Authorized trial follow-up

Root authorized one bounded local trial after the read-only assessment. The bundled Python runtime was checked first (3.12.14); the legacy tokenizer lacks its Windows wheel, so isolated Python3.10.20 was installed only under `_local/p08-local3d`. The actual pinned Torch version was upgraded to2.7.1+cu126 because the official advisory identifies a weights-only loading vulnerability in2.5.1 and earlier, fixed in2.6.0: https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6 . The original2.5.1 size survey above is not the installation recommendation.

The approved single-view Apex input retained its existing alpha. One offline grid128/chunk2048 inference completed in6.86s including loading/extraction, with1.96GB peak allocated GPU memory and2.16GB reserved. The mesh contains8,545 vertices and17,090 faces; it is watertight with consistent winding. These are execution/topology observations, not a quality or100% fidelity claim. Actual Blender visual inspection remains required. The GPU process exited before native Unity captures resumed.

Receipts: `_local/p08-local3d/outputs/apex-grid128/receipt.json`, `evidence/mesher-test.json`, `evidence/source-patches.json`, and `evidence/budget-and-packages.json`. The asymmetric CPU mesher test detected an initial inward-winding convention; the corrected adapter passes outward winding, watertightness, axis/bounds and centre checks. No background-removal model, cloud service or Blender addon was used. Conservative recorded download total4.581GB and current trial disk footprint10.133GB remain within the6GB/15GB caps.
