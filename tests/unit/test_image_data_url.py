"""image_data_url MIME detection for VLM payloads."""

from __future__ import annotations

from hylyre.vlm.http_vlm import image_data_url


def test_jpeg_prefix() -> None:
    url = image_data_url(b"\xff\xd8\xff\xe0\x00\x10jfif")
    assert url.startswith("data:image/jpeg;base64,")


def test_png_prefix() -> None:
    url = image_data_url(b"\x89PNG\r\n\x1a\n\x00")
    assert url.startswith("data:image/png;base64,")
