"""Tests for custom exceptions in echotrail_gen.exceptions."""

from __future__ import annotations

from pathlib import Path

import pytest

from echotrail_gen.exceptions import (
    EchoTrailError,
    ImageProcessingError,
    GeoProcessingError,
    TemplateNotFoundError,
    VendorFetchError,
)


class TestExceptionHierarchy:
    """Test that all custom exceptions inherit from EchoTrailError."""

    def test_image_processing_error_inherits_from_base(self):
        err = ImageProcessingError(Path("/tmp/test.jpg"), "test reason")
        assert isinstance(err, EchoTrailError)
        assert isinstance(err, Exception)

    def test_geo_processing_error_inherits_from_base(self):
        err = GeoProcessingError(Path("/tmp/test.gpx"), "test reason")
        assert isinstance(err, EchoTrailError)

    def test_template_not_found_error_inherits_from_base(self):
        err = TemplateNotFoundError(Path("/tmp/templates"))
        assert isinstance(err, EchoTrailError)

    def test_vendor_fetch_error_inherits_from_base(self):
        err = VendorFetchError("https://example.com/lib.js", "test reason")
        assert isinstance(err, EchoTrailError)


class TestImageProcessingError:
    def test_carries_path_and_reason(self):
        path = Path("/tmp/broken.jpg")
        reason = "Pillow decode error"
        err = ImageProcessingError(path, reason)
        assert err.path == path
        assert err.reason == reason

    def test_message_includes_path_and_reason(self):
        err = ImageProcessingError(Path("/tmp/broken.jpg"), "Pillow decode error")
        assert "/tmp/broken.jpg" in str(err)
        assert "Pillow decode error" in str(err)


class TestGeoProcessingError:
    def test_carries_path_and_reason(self):
        path = Path("/tmp/broken.gpx")
        reason = "Invalid XML"
        err = GeoProcessingError(path, reason)
        assert err.path == path
        assert err.reason == reason

    def test_message_includes_path_and_reason(self):
        err = GeoProcessingError(Path("/tmp/broken.gpx"), "Invalid XML")
        assert "/tmp/broken.gpx" in str(err)
        assert "Invalid XML" in str(err)


class TestTemplateNotFoundError:
    def test_carries_template_dir(self):
        path = Path("/tmp/nonexistent")
        err = TemplateNotFoundError(path)
        assert err.template_dir == path

    def test_message_includes_path(self):
        err = TemplateNotFoundError(Path("/tmp/nonexistent"))
        assert "/tmp/nonexistent" in str(err)


class TestVendorFetchError:
    def test_carries_url_and_reason(self):
        url = "https://cdn.example.com/lib.js"
        reason = "Connection timeout"
        err = VendorFetchError(url, reason)
        assert err.url == url
        assert err.reason == reason

    def test_message_includes_url_and_reason(self):
        err = VendorFetchError("https://cdn.example.com/lib.js", "Connection timeout")
        assert "https://cdn.example.com/lib.js" in str(err)
        assert "Connection timeout" in str(err)
