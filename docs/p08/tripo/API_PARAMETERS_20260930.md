# Direct Tripo V3 parameter review — 2026-09-30

Read-only review of official documentation and the local Apex receipt. No key file, wallet endpoint or generation API was accessed by this reviewer.

The request base is `https://openapi.tripo3d.ai/v3`. Image generation uses `POST /generation/image-to-model`, with `input` and `model`; the V2 `type` and `model_version` envelope does not apply. [Official V3 migration](https://developers.tripo3d.ai/en/docs/migration-v2-to-v3).

H3.1 is pinned as `model=v3.1-20260211`, with `geometry_quality=detailed` for Ultra geometry. A generation request can independently pin `texture_version=v3.5-20260815`; omitting it selects the older v3.0 texture default for H3.1. `texture_quality=extreme` is documented as 8K. These select provider capabilities; actual delivered maps and rendered fidelity still need inspection. [H-series schema](https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard), [September texture changelog](https://developers.tripo3d.ai/en/docs/changelog).

`generate_parts=true` requires **explicit** `texture=false` and `pbr=false`. Omit `quad` and `smart_low_poly` entirely: the documented `quad=true` case ignores quad output, while `smart_low_poly=true` takes precedence and suppresses parts. `pbr=true` forces texturing. The schema documents code `1004` for the forbidden textured-parts combination. [H-series compatibility rules](https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard).

## Exact generation plans

Both plans use the reviewed image upload token as `input`. Keep `enable_image_autofix=false`, `auto_size=false`, `export_uv=true`; omit `face_limit`, `compress`, `export_orientation`, `quad` and `smart_low_poly`. Adaptive source geometry can be refined and scaled in Blender. Record the submitted seed if a seed is deliberately selected.

| Field | Complete textured source | Editable geometry parts |
| --- | --- | --- |
| `model` | `v3.1-20260211` | `v3.1-20260211` |
| `geometry_quality` | `detailed` | `detailed` |
| `texture` | `true` | `false` |
| `pbr` | `true` | `false` |
| `generate_parts` | `false` | `true` |
| `texture_version` | `v3.5-20260815` | omit |
| `texture_quality` | `extreme` | omit |
| `texture_alignment` | `original_image` | omit |
| `delight` | `true` | omit |

These are alternative generation plans. A separate parts request does not establish that it reproduces the complete textured source's mesh.

## Texture stage after parts or Blender refinement

`POST /models/texture` pins the **texture** version through `model`, rather than `texture_version`. A minimum documented body for a confirmed Tripo-generated parts task is:

```json
{
  "input": "<confirmed_Tripo_generation_task_id>",
  "model": "v3.5-20260815",
  "texture_quality": "extreme",
  "texture_alignment": "original_image",
  "pbr": true,
  "delight": true,
  "bake": true
}
```

The API permits omitting `texture_prompt` for Tripo-generated task input, but recommends supplying the reference again. Its `image` mode accepts one reference; `text`, `image` and four-view `images` modes are mutually exclusive. A Blender-modified source uses its uploaded model token instead. The inspected V3 page does not provide a single-image JSON example or an explicit nested `image` value type, so this note does **not** certify a guessed token/object serialization. Validate that representation before dispatching reference-guided texturing; preserve the image hash and task lineage. [Official texture schema](https://developers.tripo3d.ai/en/docs/models-texture).

## Observed hq01 failure

`ArtSource/P08/Tripo/Apex/20260930-hq01/receipt.json` snapshot SHA256: `f58606e52672d7d043b6637e154262b17a2515890d37a5455dae20d28da5fc41`. It records HTTP 400, no task ID, original state `submission_unknown_do_not_retry`, then a retained rejection resolution. Both recorded wallet observations are 570 available and zero frozen. The submitted `generate_parts=true`, `texture=true`, `pbr=true` combination contradicts the published schema. That supports a parameter diagnosis; the HTTP error body was discarded, so **no observed API code 1004 is established**. Unchanged wallet observations alone do not prove every possible server-side outcome.

Root owns corrected client implementation, definitive rejection handling and new submissions. Every candidate remains unaccepted until source-bound Blender renders satisfy the locked concept and the existing production gate.
