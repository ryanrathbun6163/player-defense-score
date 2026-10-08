"""Load an explicitly bound adapted WASB checkpoint without changing its baseline."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re

from .wasb_adapter import WasbAdapter


class AdaptedWasbAdapter(WasbAdapter):
    """Preserve the original source/weight checks, then load named finite tensors.

    The expected derived digest and training provenance must come from the caller's
    bound training record. This class does not infer that a supplied training
    history is true; it records the exact supplied JSON alongside the loaded bytes.
    Preprocessing, heatmap extraction and prediction are inherited unchanged.
    """

    def __init__(
        self,
        source_root: str | Path,
        pretrained_path: str | Path,
        checkpoint_path: str | Path,
        checkpoint_sha256: str,
        training_provenance: dict,
        device: str = "cuda",
    ):
        import torch

        super().__init__(source_root, pretrained_path, device=device)
        if not isinstance(checkpoint_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", checkpoint_sha256) is None:
            raise ValueError("Adapted checkpoint requires an explicit lowercase SHA-256 digest")
        if (not isinstance(training_provenance, dict) or not training_provenance
                or not all(isinstance(key, str) for key in training_provenance)):
            raise ValueError("Training provenance must be a nonempty JSON object with string keys")
        try:
            provenance = json.loads(json.dumps(training_provenance, allow_nan=False, sort_keys=True))
        except (TypeError, ValueError) as error:
            raise ValueError("Training provenance must contain finite JSON values") from error

        derived_path = Path(checkpoint_path).resolve()
        # Deserialize the same bytes whose digest was checked, rather than reopen
        # a path which could have changed between verification and torch.load.
        payload = derived_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != checkpoint_sha256:
            raise ValueError("Adapted WASB checkpoint digest mismatch")
        checkpoint = torch.load(io.BytesIO(payload), map_location="cpu", weights_only=True)
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"model_state_dict"}:
            raise ValueError("Adapted checkpoint must contain only model_state_dict")
        state = checkpoint["model_state_dict"]
        if (not isinstance(state, dict) or not state
                or not all(isinstance(key, str) and isinstance(value, torch.Tensor) for key, value in state.items())):
            raise ValueError("Adapted state must contain named tensors only")
        if any(not bool(torch.isfinite(value).all()) for value in state.values()):
            raise ValueError("Adapted state contains non-finite tensors")
        self.model.load_state_dict(state, strict=True)
        self.model.eval()

        pretrained = {
            "path": self.provenance["checkpoint_path"],
            "sha256": self.provenance["checkpoint_sha256"],
            "size_bytes": self.provenance["checkpoint_size_bytes"],
        }
        self.pretrained_path = self.checkpoint_path
        self.checkpoint_path = derived_path
        self.provenance = {
            **self.provenance,
            "checkpoint_role": "adapted_basketball",
            "pretrained_checkpoint": pretrained,
            "checkpoint_path": str(derived_path),
            "checkpoint_sha256": checkpoint_sha256,
            "checkpoint_size_bytes": len(payload),
            "checkpoint_load": "verified bytes; torch.load(weights_only=True); finite tensors; load_state_dict(strict=True)",
            "training_provenance": provenance,
        }
