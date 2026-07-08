#!/usr/bin/env python3
"""
Normalize the loudness of MP3 files using ffmpeg's EBU R128 ``loudnorm`` filter.

Reads every ``*.mp3`` in an input directory (default ``mp3/speech``) and writes
a loudness-normalized copy of each into an output directory (default
``mp3/speech/normalized``).  The originals are left untouched.

Loudness normalization brings every clip to the same perceived loudness target
(``--lufs``, default -14 LUFS).  A *higher* target (closer to 0, e.g. -12 or
-11) makes the output louder; a lower target makes it quieter.  True-peak is
capped (``--tp``) to avoid clipping.

Requires ffmpeg on PATH:

    brew install ffmpeg

Usage:
    python scripts/normalize_speech.py
    python scripts/normalize_speech.py --lufs -12
    python scripts/normalize_speech.py --in mp3/speech --out mp3/speech/normalized
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Repository root (this file lives in <root>/scripts/).
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "mp3" / "speech"
DEFAULT_OUT = ROOT / "mp3" / "speech" / "normalized"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loudness-normalize MP3 files with ffmpeg loudnorm.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--in", dest="in_dir", type=Path, default=DEFAULT_IN,
        help="Directory containing the source .mp3 files.",
    )
    parser.add_argument(
        "--out", dest="out_dir", type=Path, default=DEFAULT_OUT,
        help="Directory to write normalized .mp3 files into.",
    )
    parser.add_argument(
        "--lufs", type=float, default=-14.0,
        help="Integrated loudness target in LUFS (higher = louder).",
    )
    parser.add_argument(
        "--tp", type=float, default=-1.5,
        help="Maximum true peak in dBTP (guards against clipping).",
    )
    parser.add_argument(
        "--lra", type=float, default=11.0,
        help="Target loudness range in LU.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing files in the output directory.",
    )
    return parser.parse_args()


def normalize(src: Path, dst: Path, args: argparse.Namespace) -> None:
    """Run ffmpeg loudnorm on *src*, writing the result to *dst*."""
    loudnorm = f"loudnorm=I={args.lufs}:TP={args.tp}:LRA={args.lra}"
    cmd = [
        "ffmpeg",
        "-y" if args.force else "-n",
        "-i", str(src),
        "-af", loudnorm,
        "-c:a", "libmp3lame",
        "-q:a", "2",           # VBR ~190 kbps, transparent quality
        "-loglevel", "error",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()

    if shutil.which("ffmpeg") is None:
        print(
            "error: ffmpeg not found on PATH.\n"
            "       Install it with:  brew install ffmpeg",
            file=sys.stderr,
        )
        return 1

    in_dir: Path = args.in_dir.resolve()
    out_dir: Path = args.out_dir.resolve()

    if not in_dir.is_dir():
        print(f"error: input directory does not exist: {in_dir}", file=sys.stderr)
        return 1

    # Non-recursive: this deliberately ignores the output sub-folder.
    sources = sorted(p for p in in_dir.glob("*.mp3") if p.is_file())
    if not sources:
        print(f"error: no .mp3 files found in {in_dir}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Normalizing {len(sources)} file(s) to {args.lufs} LUFS")
    print(f"  in:  {in_dir}")
    print(f"  out: {out_dir}\n")

    failures = 0
    for i, src in enumerate(sources, 1):
        dst = out_dir / src.name
        if dst.exists() and not args.force:
            print(f"[{i}/{len(sources)}] skip (exists): {src.name}")
            continue
        print(f"[{i}/{len(sources)}] {src.name}")
        try:
            normalize(src, dst, args)
        except subprocess.CalledProcessError as exc:
            failures += 1
            print(f"    FAILED (ffmpeg exit {exc.returncode})", file=sys.stderr)

    print()
    if failures:
        print(f"Done with {failures} failure(s).", file=sys.stderr)
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
