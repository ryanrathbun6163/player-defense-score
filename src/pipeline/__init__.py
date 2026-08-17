"""Configuration foundation for the player-coordinate pipeline."""

from .possession import (
    ConfigurationError,
    CourtModel,
    PipelineManifest,
    PipelinePaths,
    load_manifest,
)

__all__ = [
    "ConfigurationError",
    "CourtModel",
    "PipelineManifest",
    "PipelinePaths",
    "load_manifest",
]
