"""Custom exceptions for EchoTrail operations.

Provides typed, domain-specific exceptions that carry context for better
error handling and debugging compared to generic Exception types.
"""

from __future__ import annotations

from pathlib import Path


class EchoTrailError(Exception):
    """Base exception for all EchoTrail-specific errors."""

    pass


class ImageProcessingError(EchoTrailError):
    """Raised when image resizing or thumbnail generation fails.

    Attributes:
        path: The path to the image file that failed processing
        reason: Human-readable explanation of why processing failed
    """

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to process image {path}: {reason}")


class GeoProcessingError(EchoTrailError):
    """Raised when GPX or GeoJSON processing fails.

    Attributes:
        path: The path to the geo file that failed processing
        reason: Human-readable explanation of why processing failed
    """

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to process geo file {path}: {reason}")


class TemplateNotFoundError(EchoTrailError):
    """Raised when required template files are missing.

    Attributes:
        template_dir: The directory that was expected to contain templates
    """

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        super().__init__(f"Templates directory not found: {template_dir}")


class VendorFetchError(EchoTrailError):
    """Raised when downloading vendor assets (Leaflet, GLightbox) fails.

    Attributes:
        url: The URL that failed to download
        reason: Human-readable explanation of the failure
    """

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to fetch {url}: {reason}")
