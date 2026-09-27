# Pictures: first bake-off (2026-09-26)

Engine: stable-diffusion.cpp master-920 (MIT), Vulkan build on the workstation's Radeon 6900XT (16 GB)
and the CPU build. Prompt: "top-down seamless game tile, warm honey-coloured wooden floorboards, cozy
storybook painting, soft cel shading, warm brown outlines", seed 7. The CPU was also running other
benchmarks, so CPU times are upper bounds.

| Model (licence) | Where | Size | Steps | Time | Result |
|---|---|---|---|---|---|
| SD-Turbo (Stability Community, $1M cap) | CPU, 8 threads | 512 | 1 | 128 s incl. load | wrong subject (stone blocks), off-style: `sdturbo-wood.png` |
| FLUX.2-klein-4B Q8 + Qwen3-4B Q8 + small decoder (all Apache) | GPU (Vulkan) | 512 | 4 | 9.3 s sampling, 19.4 s total, 8.3 GB VRAM | right subject, storybook feel: `klein-wood.png` |
| same, with our wood tile as reference (`-r`) | GPU | 512 | 4 | 10.2 s sampling | matches the house style closely: `klein-table-ref.png` |
| same | CPU, 8 threads | 256 | 4 | 315 s sampling, 388 s total, 8 GB RAM | drifted (furniture on the floor): `klein-wood-cpu256.png` |

Reading: FLUX.2-klein is the GPU tier (the studio's big painter, and the teacher that can paint on-style
training art locally from one reference). It is too slow for the CPU tier; that stays a small model plus
a storybook style LoRA, still to be trained and measured.

## The storybook style add-on (LoRA) on SD-Turbo, CPU

Trained on the 6900XT (kohya sd-scripts, ROCm 6.4 PyTorch): 142 storybook pictures (Wan, paid plan),
trigger `vefrstyle`, dim 16, 6 epochs, about 27 minutes; 27 MB file. CPU, 4 steps, 512px, seed 21,
about 4 minutes per picture on a CPU shared with other benchmarks.

`lora-baker-strengths.png`, left to right: no add-on; epoch 2 at 1.0; **final at 0.5**; epoch 4 at
0.7; final at 1.0. At full strength the add-on blurs (it partly undoes SD-Turbo's few-step
distillation); **at 0.5 it keeps the detail and pulls clearly toward the storybook look**. The floor tile
at full strength finally paints floorboards (the right subject) but soft: `lora-floor-potion-full-strength.png`.
Next: retrain on the 334-picture set; sweep strength 0.4 to 0.6.
