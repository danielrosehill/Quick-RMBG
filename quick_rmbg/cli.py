"""CLI wrapper for Quick-RMBG background removal."""

import subprocess
import sys
from pathlib import Path

from .config import get_rembg_binary, get_output_suffix, get_model, get_rocm_gfx_version

# Supported image formats
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def _run_rembg(input_path: Path, output_path: Path, rembg_binary: Path, model: str, env: dict) -> tuple[bool, str]:
    """
    Run rembg on a single image.

    Args:
        input_path: Path to input image
        output_path: Path for output
        rembg_binary: Path to rembg binary
        model: Model name to use
        env: Environment variables

    Returns:
        Tuple of (success, error_message or empty string)
    """
    try:
        result = subprocess.run(
            [str(rembg_binary), "i", str(input_path), str(output_path), "-m", model],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,  # 2 minute timeout
        )

        if result.returncode == 0:
            return True, ""
        else:
            error = result.stderr or result.stdout or "Unknown error"
            return False, error

    except subprocess.TimeoutExpired:
        return False, "Operation timed out (>2 minutes)"
    except Exception as e:
        return False, str(e)


def _prepare_rembg() -> tuple[Path | None, str, dict, str]:
    """
    Prepare rembg for execution.

    Returns:
        Tuple of (rembg_binary, model, env, error_message)
    """
    import os

    rembg_binary = get_rembg_binary()
    if rembg_binary is None:
        return None, "", {}, "rembg not found.\nInstall it with: pip install rembg[cli]"

    model = get_model()

    env = os.environ.copy()
    rocm_gfx = get_rocm_gfx_version()
    if rocm_gfx:
        env["HSA_OVERRIDE_GFX_VERSION"] = rocm_gfx

    return rembg_binary, model, env, ""


def remove_background(input_path: Path, output_path: Path | None = None) -> tuple[bool, str]:
    """
    Remove background from an image using rembg.

    Args:
        input_path: Path to input image
        output_path: Path for output (default: input_noBG.png)

    Returns:
        Tuple of (success, message)
    """
    # Validate input
    if not input_path.exists():
        return False, f"File not found: {input_path}"

    if input_path.suffix.lower() not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {input_path.suffix}"

    # Prepare rembg
    rembg_binary, model, env, error = _prepare_rembg()
    if rembg_binary is None:
        return False, error

    # Determine output path
    if output_path is None:
        suffix = get_output_suffix()
        # Output is always PNG (transparency support)
        output_path = input_path.parent / f"{input_path.stem}{suffix}.png"

    success, error = _run_rembg(input_path, output_path, rembg_binary, model, env)

    if success:
        return True, f"Background removed.\nSaved to: {output_path.name}"
    else:
        return False, f"rembg failed: {error}"


def remove_background_two_pass(input_path: Path) -> tuple[bool, str]:
    """
    Remove background from an image using rembg in two passes.

    First pass saves to input_noBG-first-pass.png
    Second pass saves to input_noBG-second-pass.png

    Args:
        input_path: Path to input image

    Returns:
        Tuple of (success, message)
    """
    # Validate input
    if not input_path.exists():
        return False, f"File not found: {input_path}"

    if input_path.suffix.lower() not in SUPPORTED_FORMATS:
        return False, f"Unsupported format: {input_path.suffix}"

    # Prepare rembg
    rembg_binary, model, env, error = _prepare_rembg()
    if rembg_binary is None:
        return False, error

    # First pass output path
    first_pass_path = input_path.parent / f"{input_path.stem}_noBG-first-pass.png"

    # Run first pass
    success, error = _run_rembg(input_path, first_pass_path, rembg_binary, model, env)
    if not success:
        return False, f"First pass failed: {error}"

    # Second pass output path
    second_pass_path = input_path.parent / f"{input_path.stem}_noBG-second-pass.png"

    # Run second pass on the first pass result
    success, error = _run_rembg(first_pass_path, second_pass_path, rembg_binary, model, env)
    if not success:
        return False, f"Second pass failed: {error}"

    return True, f"Two-pass background removal complete.\nFirst pass: {first_pass_path.name}\nFinal: {second_pass_path.name}"


def show_notification(title: str, message: str, success: bool = True) -> None:
    """Show a desktop notification using kdialog or notify-send."""
    icon = "dialog-ok" if success else "dialog-error"

    # Try kdialog first (KDE native)
    try:
        subprocess.run(
            ["kdialog", "--passivepopup", message, "5", "--title", title, "--icon", icon],
            check=True,
            capture_output=True,
        )
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fall back to notify-send
    try:
        subprocess.run(
            ["notify-send", "-i", icon, title, message],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Last resort: print to stderr
        print(f"{title}: {message}", file=sys.stderr)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Quick background removal for images",
        prog="quick-rmbg",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input image file",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output file path (default: input_noBG.png)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress desktop notifications",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Don't show desktop notification (print to stdout instead)",
    )
    parser.add_argument(
        "--two-pass",
        action="store_true",
        help="Run background removal twice for better results",
    )

    args = parser.parse_args()

    if args.two_pass:
        success, message = remove_background_two_pass(args.input)
        title = "Quick RMBG (Two-Pass)"
    else:
        success, message = remove_background(args.input, args.output)
        title = "Quick RMBG"

    if args.no_notify or args.quiet:
        if not args.quiet:
            print(message)
    else:
        show_notification(
            title,
            message,
            success=success,
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
