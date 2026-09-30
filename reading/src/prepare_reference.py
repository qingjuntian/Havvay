"""Trim a reference recording and save the user-supplied transcript."""

from __future__ import annotations

import argparse
import io
import subprocess
import wave
from pathlib import Path

import numpy as np


def trim_silence(samples: np.ndarray, sample_rate: int, threshold: float, pad: float) -> np.ndarray:
    mono = samples.mean(axis=1) if samples.ndim > 1 else samples
    frame = max(1, int(sample_rate * 0.02))
    rms = np.sqrt(np.mean(np.square(mono[: len(mono) // frame * frame].reshape(-1, frame)), axis=1))
    active = np.flatnonzero(rms >= threshold)
    if not len(active):
        raise ValueError("Reference audio contains no sound above the silence threshold")
    start = max(0, int(active[0] * frame - pad * sample_rate))
    end = min(len(samples), int((active[-1] + 1) * frame + pad * sample_rate))
    return samples[start:end]


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "24000", "-f", "wav", "pipe:1"],
        check=True,
        stdout=subprocess.PIPE,
    )
    with wave.open(io.BytesIO(result.stdout), "rb") as source:
        sample_rate = source.getframerate()
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sample_rate


def write_audio(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    pcm = np.clip(samples * 32768.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Trim silence from a voice reference.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--text-output", default=None)
    parser.add_argument("--ref-text", default=None, help="Exact transcript of the retained audio")
    parser.add_argument("--max-seconds", type=float, default=12.0)
    parser.add_argument("--threshold", type=float, default=0.015)
    parser.add_argument("--pad", type=float, default=0.08)
    args = parser.parse_args()

    samples, sample_rate = read_audio(Path(args.input))
    trimmed = trim_silence(samples, sample_rate, args.threshold, args.pad)
    duration = len(trimmed) / sample_rate
    if duration > args.max_seconds:
        raise SystemExit(f"Trimmed reference is {duration:.2f}s; shorten the source or increase --max-seconds")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_audio(Path(args.output), trimmed, sample_rate)
    if args.ref_text and not args.text_output:
        raise SystemExit("--text-output is required when --ref-text is provided")
    if args.text_output and args.ref_text:
        text_output = Path(args.text_output)
        text_output.parent.mkdir(parents=True, exist_ok=True)
        text_output.write_text(args.ref_text.strip() + "\n", encoding="utf-8")
        print(f"Wrote {args.output}: {duration:.2f}s; transcript saved to {text_output}")
    else:
        print(f"Wrote {args.output}: {duration:.2f}s; transcript not supplied")


if __name__ == "__main__":
    main()
