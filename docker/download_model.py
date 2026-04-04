import os
import sys
import torch

model_id = os.environ.get("QWEN3_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
cache_dir = os.environ.get("HF_HOME", "/opt/hf_cache")
token = os.environ.get("HF_TOKEN") or None

# Align HF_HUB_CACHE with cache_dir so sub-models (e.g. speech_tokenizer) loaded
# internally by Qwen3TTSModel resolve to the same directory as the main model.
# Without this, HF_HUB_CACHE defaults to HF_HOME/hub, creating a path mismatch.
os.environ["HF_HUB_CACHE"] = cache_dir

print(f"Downloading and caching {model_id} to {cache_dir} ...")
try:
    from qwen_tts import Qwen3TTSModel

    # Actually load the model to ensure all dependencies (including nested ones like speech_tokenizer) are cached
    model = Qwen3TTSModel.from_pretrained(
        model_id,
        cache_dir=cache_dir,
        token=token,
        device_map="cpu",
        dtype=torch.float32,
        trust_remote_code=True,
    )
    print(f"Model {model_id} successfully downloaded and cached")
    del model
except Exception as e:
    print(f"ERROR: Model download/cache failed: {e}", file=sys.stderr)
    sys.exit(1)
