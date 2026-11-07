"""HTTP wrapper around the pretrained YOLO detectors (demo output only)."""

from __future__ import annotations

from .app import DEMO_WARNING, create_app

__all__ = ["DEMO_WARNING", "create_app"]
