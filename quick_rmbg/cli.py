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


def _ask_user_happy(image_path: Path, pass_number: int) -> bool:
    """
    Ask the user if they're happy with the result using kdialog.

    Args:
        image_path: Path to the result image to show
        pass_number: Current pass number for display

    Returns:
        True if user is happy, False if they want another pass
    """
    message = f"Pass {pass_number} complete!\n\nResult saved to:\n{image_path.name}\n\nAre you happy with the result?"

    try:
        # Use kdialog yesno dialog
        result = subprocess.run(
            [
                "kdialog",
                "--yesno",
                message,
                "--title",
                "Quick RMBG - Infinite Hop Mode",
                "--yes-label",
                "Yes, I'm done!",
                "--no-label",
                "No, run another pass",
            ],
            capture_output=True,
        )
        # kdialog returns 0 for Yes, 1 for No
        return result.returncode == 0

    except FileNotFoundError:
        # Fall back to zenity if kdialog not available
        try:
            result = subprocess.run(
                [
                    "zenity",
                    "--question",
                    "--text",
                    message,
                    "--title",
                    "Quick RMBG - Infinite Hop Mode",
                    "--ok-label",
                    "Yes, I'm done!",
                    "--cancel-label",
                    "No, run another pass",
                ],
                capture_output=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            # No GUI available, assume user is happy after first pass
            print("No dialog tool available (kdialog/zenity). Stopping after this pass.")
            return True


def remove_background_infinite_hop(input_path: Path) -> tuple[bool, str]:
    """
    Remove background from an image using rembg with infinite passes.

    Runs rembg, asks user if happy, and repeats until satisfied.
    Each pass saves to input_noBG-pass-N.png

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

    pass_number = 1
    current_input = input_path
    final_output = None
    all_passes = []

    while True:
        # Output path for this pass
        output_path = input_path.parent / f"{input_path.stem}_noBG-pass-{pass_number}.png"

        # Run rembg
        success, error = _run_rembg(current_input, output_path, rembg_binary, model, env)
        if not success:
            return False, f"Pass {pass_number} failed: {error}"

        all_passes.append(output_path.name)
        final_output = output_path

        # Ask user if they're happy
        if _ask_user_happy(output_path, pass_number):
            break

        # User wants another pass - use this output as next input
        current_input = output_path
        pass_number += 1

    # Build summary message
    if pass_number == 1:
        return True, f"Infinite Hop complete after 1 pass.\nFinal: {final_output.name}"
    else:
        passes_list = "\n".join(f"  Pass {i+1}: {p}" for i, p in enumerate(all_passes))
        return True, f"Infinite Hop complete after {pass_number} passes.\n{passes_list}\nFinal: {final_output.name}"


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
    parser.add_argument(
        "--infinite-hop",
        action="store_true",
        help="Run background removal repeatedly until you're happy with the result",
    )

    args = parser.parse_args()

    # Check for conflicting options
    if args.two_pass and args.infinite_hop:
        print("Error: Cannot use --two-pass and --infinite-hop together", file=sys.stderr)
        sys.exit(1)

    if args.infinite_hop:
        success, message = remove_background_infinite_hop(args.input)
        title = "Quick RMBG (Infinite Hop)"
    elif args.two_pass:
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
