#!/usr/bin/env python3
"""
Increase the loudness of MP3 files by a fixed dB gain using ffmpeg.

Applies a flat gain (``--db``, default +5 dB) to every ``*.mp3`` in a directory
(default ``mp3/speech/normalized``) via ffmpeg's ``volume`` filter.

By default the files are boosted **in place** (written via a temporary file
that atomically replaces the original).  Pass ``--out DIR`` to write the
boosted copies into a separate directory and leave the originals untouched.

Clipping warning:
    A flat gain does not respect headroom.  If the source already peaks near
    0 dBFS (loudness-normalized files typically do), a positive gain will push
    peaks past full scale and ffmpeg will hard-clip them, causing distortion.
    Pass ``--limit`` to insert a true-peak limiter after the gain so peaks are
    caught cleanly instead of clipped.

Requires ffmpeg on PATH:

    brew install ffmpeg

Usage:
    python scripts/boost_gain.py                       # +5 dB, in place
    python scripts/boost_gain.py --db 3                # +3 dB instead
    python scripts/boost_gain.py --limit               # +5 dB, no hard clipping
    python scripts/boost_gain.py --out mp3/speech/loud # write copies elsewhere
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Repository root (this file lives in <root>/scripts/).
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "mp3" / "speech" / "normalized"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Boost MP3 loudness by a fixed dB gain with ffmpeg.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--in", dest="in_dir", type=Path, default=DEFAULT_IN,
        help="Directory containing the source .mp3 files.",
    )
    parser.add_argument(
        "--out", dest="out_dir", type=Path, default=None,
        help="Write boosted copies here instead of editing in place.",
    )
    parser.add_argument(
        "--db", type=float, default=5.0,
        help="Gain to apply, in dB (positive = louder).",
    )
    parser.add_argument(
        "--limit", action="store_true",
        help="Insert a true-peak limiter after the gain to avoid hard clipping.",
    )
    return parser.parse_args()


def build_filter(args: argparse.Namespace) -> str:
    """Return the ffmpeg -af filter chain for the requested gain."""
    chain = f"volume={args.db}dB"
    if args.limit:
        # Catch anything the gain pushed past ~-1 dBTP instead of clipping it.
        chain += ",alimiter=limit=0.891"  # 0.891 ≈ -1 dBFS
    return chain


def boost(src: Path, dst: Path, args: argparse.Namespace) -> None:
    """Run ffmpeg on *src*, writing the gained result to *dst*."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-af", build_filter(args),
        "-c:a", "libmp3lame",
        "-q:a", "2",           # VBR ~190 kbps, transparent quality
        "-loglevel", "error",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def boost_in_place(src: Path, args: argparse.Namespace) -> None:
    """Boost *src* in place via a temp file that atomically replaces it."""
    with tempfile.NamedTemporaryFile(
        dir=src.parent, prefix=".boost-", suffix=".mp3", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        boost(src, tmp_path, args)
        tmp_path.replace(src)  # atomic on the same filesystem
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


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
    if not in_dir.is_dir():
        print(f"error: input directory does not exist: {in_dir}", file=sys.stderr)
        return 1

    sources = sorted(p for p in in_dir.glob("*.mp3") if p.is_file())
    if not sources:
        print(f"error: no .mp3 files found in {in_dir}", file=sys.stderr)
        return 1

    out_dir: Path | None = None
    if args.out_dir is not None:
        out_dir = args.out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

    where = f"in place in {in_dir}" if out_dir is None else f"to {out_dir}"
    limiter = " (with peak limiter)" if args.limit else ""
    print(f"Applying {args.db:+g} dB gain{limiter} to {len(sources)} file(s) {where}\n")

    failures = 0
    for i, src in enumerate(sources, 1):
        print(f"[{i}/{len(sources)}] {src.name}")
        try:
            if out_dir is None:
                boost_in_place(src, args)
            else:
                boost(src, out_dir / src.name, args)
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
