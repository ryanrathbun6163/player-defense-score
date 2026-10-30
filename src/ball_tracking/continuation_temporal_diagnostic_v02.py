"""Explicit supervised entry for the additive diagnostic guard correction."""
from pathlib import Path
import hashlib
HELPER = "data/outputs/t/wasb_continuation_20261026/middle_output_sensitivity_launchable_v02.py"
HELPER_SHA256 = "c0a91a0314c0eba0a10b46bbff81da27a861f779db2294a99dc6e7fca5c8814d"
def main():
    root = Path(__file__).resolve().parents[2]
    path = root / HELPER
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != HELPER_SHA256:
        raise ValueError("Pinned diagnostic helper changed")
    exec(compile(payload, str(path), "exec"), {"__name__": "__main__", "__file__": str(path), "__package__": None})
if __name__ == "__main__": main()
