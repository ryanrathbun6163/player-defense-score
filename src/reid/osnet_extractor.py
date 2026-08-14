from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as functional
from huggingface_hub import hf_hub_download

from src.reid.osnet_ain import osnet_ain_x1_0


MODEL_REPOSITORY = "kaiyangzhou/osnet"

MODEL_FILENAME = (
    "osnet_ain_x1_0_msmt17_256x128_amsgrad_"
    "ep50_lr0.0015_coslr_b64_fb10_softmax_"
    "labsmth_flip_jitter.pth"
)

INPUT_WIDTH = 128
INPUT_HEIGHT = 256

IMAGENET_MEAN = torch.tensor(
    [0.485, 0.456, 0.406],
    dtype=torch.float32,
).view(3, 1, 1)

IMAGENET_STD = torch.tensor(
    [0.229, 0.224, 0.225],
    dtype=torch.float32,
).view(3, 1, 1)


class OSNetExtractor:
    def __init__(
        self,
        device=None,
        batch_size=64,
    ):
        if device is None:
            device = (
                "cuda"
                if torch.cuda.is_available()
                else "cpu"
            )

        self.device = torch.device(device)
        self.batch_size = batch_size

        self.model_path = Path(
            hf_hub_download(
                repo_id=MODEL_REPOSITORY,
                filename=MODEL_FILENAME,
            )
        )

        self.model = osnet_ain_x1_0(
            num_classes=1,
            pretrained=False,
        )

        self._load_reid_weights()

        self.model.to(self.device)
        self.model.eval()

        print(
            "OSNet-AIN ready on "
            f"{self.device}"
        )
        print(
            f"Weights: {self.model_path}"
        )

    def _load_reid_weights(self):
        checkpoint = torch.load(
            self.model_path,
            map_location="cpu",
            weights_only=True,
        )

        model_state = self.model.state_dict()
        compatible_state = {}

        for key, value in checkpoint.items():
            clean_key = key

            if clean_key.startswith("module."):
                clean_key = clean_key[7:]

            if (
                clean_key in model_state
                and model_state[clean_key].shape
                == value.shape
            ):
                compatible_state[
                    clean_key
                ] = value

        if not compatible_state:
            raise RuntimeError(
                "No compatible OSNet weights "
                "were found in the checkpoint"
            )

        load_result = self.model.load_state_dict(
            compatible_state,
            strict=False,
        )

        non_classifier_missing = [
            key
            for key in load_result.missing_keys
            if not key.startswith("classifier.")
        ]

        if non_classifier_missing:
            raise RuntimeError(
                "OSNet checkpoint is missing "
                "non-classifier layers: "
                f"{non_classifier_missing}"
            )

        print(
            "Loaded "
            f"{len(compatible_state)} "
            "OSNet parameter tensors"
        )

    @staticmethod
    def _prepare_crop(crop_bgr):
        if crop_bgr is None or crop_bgr.size == 0:
            raise ValueError(
                "Cannot extract an embedding "
                "from an empty crop"
            )

        resized_bgr = cv2.resize(
            crop_bgr,
            (INPUT_WIDTH, INPUT_HEIGHT),
            interpolation=cv2.INTER_CUBIC,
        )

        resized_rgb = cv2.cvtColor(
            resized_bgr,
            cv2.COLOR_BGR2RGB,
        )

        tensor = torch.from_numpy(
            resized_rgb
        ).permute(2, 0, 1)

        tensor = tensor.to(
            dtype=torch.float32
        ) / 255.0

        tensor = (
            tensor - IMAGENET_MEAN
        ) / IMAGENET_STD

        return tensor

    def extract(self, crops_bgr):
        if not crops_bgr:
            return np.empty(
                (0, 512),
                dtype=np.float32,
            )

        prepared_crops = [
            self._prepare_crop(crop)
            for crop in crops_bgr
        ]

        embedding_batches = []

        with torch.inference_mode():
            for batch_start in range(
                0,
                len(prepared_crops),
                self.batch_size,
            ):
                batch_tensors = (
                    prepared_crops[
                        batch_start:
                        batch_start
                        + self.batch_size
                    ]
                )

                batch = torch.stack(
                    batch_tensors
                ).to(self.device)

                embeddings = self.model(batch)

                embeddings = functional.normalize(
                    embeddings,
                    p=2,
                    dim=1,
                )

                embedding_batches.append(
                    embeddings.cpu().numpy()
                )

        return np.concatenate(
            embedding_batches,
            axis=0,
        ).astype(np.float32)