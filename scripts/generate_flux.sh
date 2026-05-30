#!/bin/bash

PROMPT="$1"
WIDTH="${2:-768}"
HEIGHT="${3:-768}"

cat > /tmp/flux_request.json <<EOF
{
  "prompt": {
    "1": {
      "class_type": "Text to Image (Flux.1 Dev)",
      "inputs": {
        "text": "$PROMPT",
        "width": $WIDTH,
        "height": $HEIGHT,
        "seed": 0,
        "unet_name": "flux1-dev.safetensors",
        "clip_name1": "clip_l.safetensors",
        "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
        "vae_name": "ae.safetensors"
      }
    },
    "2": {
      "class_type": "SaveImage",
      "inputs": {
        "filename_prefix": "flux_cli",
        "images": ["1", 0]
      }
    }
  }
}
EOF

curl -X POST http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d @/tmp/flux_request.json
  