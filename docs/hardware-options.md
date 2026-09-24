# Hardware Options for Local OCR and VLM

Where Vigil's two OCR workloads can run, and the trade-offs of each option. Nothing here is decided yet (see [revisit-later.md](revisit-later.md) #5).

The two workloads:
- **Finding PII on every page.** Classic OCR with word positions: PP-OCRv5 or v6 plus docTR. It's cheap and runs acceptably on CPU.
- **Reading hard pages.** A local VLM (PaddleOCR-VL-1.6 or GLM-OCR, both ~0.9B parameters). This is the heavy one: roughly 30× faster on a GPU than on a CPU.

All three machines sit inside the Practice Boundary, so any of them may read identifiable pages ([ADR 0001](adr/0001-deidentify-before-leaving-practice.md)). Traffic between machines must be encrypted, and worker machines must not keep documents after processing them.

Figures marked *est.* are extrapolations and have not been measured; *T4* means measured on a comparable GPU (NVIDIA T4). Measure everything against the Reference Set before relying on it.

## Machines

### 1. MacBook (Apple Silicon): development machine

| Option | PII OCR | VLM s/page | Pros | Cons |
|---|---|---|---|---|
| **1a. Everything in Docker** | ~1–3 s (PP-OCRv5, CPU) | *est.* 30–120 | One `docker compose up`, the same setup as production | Docker on a Mac can't use the GPU. Paddle's official images are built for Intel chips, so they run under emulation (very slow) unless we use ARM builds of llama.cpp. |
| **1b. App in Docker, VLM on the host with MLX** | same | *est.* 3–10 | Uses the Mac's GPU. Official MLX conversions exist for 1.5; the 1.6 conversions are community-made. | Two things to run. mlx-vlm has open loader bugs. Differs from production. |
| **1c. App in Docker, VLM on the host with llama.cpp (Metal)** | same | *est.* 3–10 | Official GGUF files for PaddleOCR-VL-1.6 and GLM-OCR. The same engine can run on the RTX 2060 and a Beelink. | llama.cpp reportedly reduces PaddleOCR-VL quality, so check it on the Reference Set. |
| **1d. Nothing in Docker** | same | as 1b/1c | Simplest for fast development | Breaks the "everything in Docker" rule; environments drift. |

### 2. Old Windows PC with an RTX 2060 (6 GB): candidate GPU worker

Runs through WSL2 and the NVIDIA Container Toolkit. It's an older GPU generation (Turing): no bf16, no FlashAttention-2.

| Option | VLM s/page | Pros | Cons |
|---|---|---|---|
| **2a. llama.cpp with CUDA, Q8 GGUF (~1 GB)** | *est.* 3–8 | Most likely to fit in 6 GB. Same engine as 1c. | Possible quality loss (as 1c). |
| **2b. vLLM fp16** | 2–3 (*T4*) | Fastest | Paddle's docs say it's "prone to timeouts or OOM" on this GPU generation. Their smallest tested GPU has 12 GB. |
| **2c. PaddlePaddle GPU (default pipeline)** | *est.* 10–40 | Official path, full layout pipeline | Likely to run out of memory on 6 GB. |
| PP-OCRv5 / docTR on GPU | <0.3 s | Low risk | none |

Overall: an old machine, and Windows adds WSL2 complexity. Good for measuring and for a pilot, but questionable as the practice's permanent server.

### 3. Beelink (or similar) mini PC with 32 GB RAM: candidate practice server

Not yet chosen. Models range from Intel N100 (weak) to AMD Ryzen 7/9 with Radeon 780M/890M integrated graphics. *Nothing here is measured.*

| Option | VLM s/page | Pros | Cons |
|---|---|---|---|
| **3a. Linux + Docker, CPU only** | *est.* 20–90 (Ryzen); much slower on N100 | Small, quiet, cheap, runs all the time, native Docker on Linux | Slow for the VLM. Fine only if VLM reads happen in the background and aren't needed often. |
| **3b. llama.cpp with Vulkan on the integrated GPU** | *est.* 8–30 | Uses the integrated GPU with no NVIDIA dependency | Support for vision models on Vulkan is less mature. Needs measuring. |
| **3c. Beelink as server + RTX 2060 box as GPU worker** | as 2a | Always-on server with GPU speed when needed | Two machines to maintain. |

If buying: prefer a Ryzen 7/9 model (e.g. 780M or better) over N100 models. 32 GB of RAM is plenty; the models need about 2–4 GB.

## Recommendation for now

- **Development:** 1c. App in Docker on the Mac; the VLM runs on the host through llama.cpp with Metal.
- **Pilot:** 2a. The RTX 2060 box serves the VLM over the LAN.
- **Production:** decide after measuring. The pipeline talks to the VLM as a swappable HTTP worker, so any machine can host it.
