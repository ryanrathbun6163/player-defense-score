"""Explicit supervised entry for the bound, optional eight-call diagnostic.

No model runs by default. The bound helper requires an explicit mode, completed
comparison evidence, checkpoint identity and the active owned GPU supervisor.
"""
from pathlib import Path
import hashlib


HELPER = "data/outputs/t/wasb_continuation_20261026/middle_output_sensitivity_launchable_v0_1.py"
HELPER_SHA256 = "acb2c91a971aba9f171669792fdca70e48bbde9fb02ce7785061e34ae8494504"


def main():
    root = Path(__file__).resolve().parents[2]
    path = root / HELPER
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != HELPER_SHA256:
        raise ValueError("Pinned continuation diagnostic helper changed")
    # Execute the same verified bytes; no caller-supplied module or script path.
    exec(compile(payload, str(path), "exec"),
         {"__name__": "__main__", "__file__": str(path), "__package__": None})


if __name__ == "__main__":
    main()
