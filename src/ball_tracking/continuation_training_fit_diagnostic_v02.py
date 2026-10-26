"""Explicit supervised entry for the additive diagnostic guard correction."""
from pathlib import Path
import hashlib
HELPER = "data/outputs/t/wasb_continuation_20261026/current768_training_fit_v02.py"
HELPER_SHA256 = "9b391df90c2b4b7acf03f7bd84d0700941d281e541ceb5960d03442380e950ab"
def main():
    root = Path(__file__).resolve().parents[2]
    path = root / HELPER
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != HELPER_SHA256:
        raise ValueError("Pinned diagnostic helper changed")
    exec(compile(payload, str(path), "exec"), {"__name__": "__main__", "__file__": str(path), "__package__": None})
if __name__ == "__main__": main()
