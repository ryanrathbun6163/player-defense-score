"""Separate fresh-stat accounting candidate with one prefix per directory.

The ordinary supervisor does not install this candidate. Performance readiness
and recovery integration remain separate approval and validation steps.
"""
from __future__ import annotations

import os
import time

from .crop_retention_resources import ResourceLimitError


def output_bytes(root):
    # Retain the full two-inventory contract and all existing deadline checks.
    # Only path construction changes, with its own additional deadline check.
    deadline = time.monotonic() + .5

    def check_deadline():
        if time.monotonic() >= deadline:
            raise ResourceLimitError("Output tree did not stabilize for complete byte accounting")

    previous = None
    while True:
        check_deadline()
        try:
            current = {}

            def fail(error):
                raise error

            for folder, _, files in os.walk(root, onerror=fail):
                check_deadline()
                # A nonempty placeholder also preserves the separator at UNC roots.
                prefix = os.path.join(folder, "_")[:-1]
                check_deadline()
                for name in files:
                    check_deadline()
                    info = os.stat(prefix + name)
                    check_deadline()
                    identity = (info.st_dev, info.st_ino)
                    count, size = current.get(identity, (0, 0))
                    current[identity] = (count + 1, max(size, info.st_size))
            check_deadline()
            if (previous is not None and previous.keys() <= current.keys()
                    and all(current[key][0] >= count for key, (count, _) in previous.items())):
                measured = sum(count * max(size, previous.get(key, (0, 0))[1])
                               for key, (count, size) in current.items())
                check_deadline()
                return measured
            previous = current
        except FileNotFoundError:
            previous = None
        check_deadline()
