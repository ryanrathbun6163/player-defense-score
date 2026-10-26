"""Explicit supervised entry for one bound current768 training-fit census."""
from pathlib import Path
import hashlib


HELPER = "data/outputs/t/wasb_continuation_20261026/current768_training_fit.py"
HELPER_SHA256 = "4bcf01843d910ce04d5c2f9bb650d2c98b36f6a15f3da808d910e776c4d845ef"


def main():
    root = Path(__file__).resolve().parents[2]
    path = root / HELPER
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != HELPER_SHA256:
        raise ValueError("Pinned current768 training-fit helper changed")
    exec(compile(payload, str(path), "exec"),
         {"__name__": "__main__", "__file__": str(path), "__package__": None})


if __name__ == "__main__":
    main()
