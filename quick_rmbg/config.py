"""Configuration management for Quick-RMBG."""

import json
import shutil
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "quick-rmbg" / "config.json"

DEFAULT_CONFIG = {
    "rembg_binary": "",  # Auto-detected if empty
    "output_suffix": "_noBG",
    "model": "u2net",  # Options: u2net, u2netp, u2net_human_seg, silueta, isnet-general-use
    "rocm_gfx_version": "11.0.1",  # For AMD ROCm; set to null/empty for NVIDIA/CPU
}


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration from file, or return defaults."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
            # Merge with defaults for any missing keys
            return {**DEFAULT_CONFIG, **saved}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Save configuration to file."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def find_rembg_binary() -> Path | None:
    """Find rembg binary in PATH or common locations."""
    # Check PATH first
    rembg = shutil.which("rembg")
    if rembg:
        return Path(rembg)

    # Check common locations
    common_paths = [
        Path.home() / ".local" / "bin" / "rembg",
        Path("/usr/local/bin/rembg"),
        Path("/usr/bin/rembg"),
    ]
    for path in common_paths:
        if path.exists():
            return path

    return None


def get_rembg_binary() -> Path | None:
    """Get the path to the rembg binary."""
    config = load_config()

    # If explicitly configured, use that
    if config.get("rembg_binary"):
        path = Path(config["rembg_binary"])
        if path.exists():
            return path

    # Otherwise auto-detect
    return find_rembg_binary()


def get_output_suffix() -> str:
    """Get the suffix to append to output files."""
    config = load_config()
    return config["output_suffix"]


def get_model() -> str:
    """Get the model to use for background removal."""
    config = load_config()
    return config.get("model", "u2net")


def set_rembg_binary(path: str) -> None:
    """Set the rembg binary path in config."""
    config = load_config()
    config["rembg_binary"] = path
    save_config(config)


def get_rocm_gfx_version() -> str | None:
    """Get the ROCm GFX version for AMD GPUs. Returns None if disabled."""
    config = load_config()
    version = config.get("rocm_gfx_version", "11.0.1")
    # Treat empty string or null as disabled
    if not version:
        return None
    return version
