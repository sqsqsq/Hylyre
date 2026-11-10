"""VLM uses the same complete-image rule as file publication."""
import base64
import pytest
from hylyre.vlm.http_vlm import image_data_url
from tests.image_samples import image_bytes, invalid_images

@pytest.mark.parametrize("format", ["JPEG", "PNG"])
def test_mime_and_original_bytes(format):
    raw = image_bytes(format)
    prefix, payload = image_data_url(raw).split(",", 1)
    assert prefix == "data:image/" + format.lower() + ";base64"
    assert base64.b64decode(payload) == raw

@pytest.mark.parametrize("raw", invalid_images())
def test_invalid_images_rejected(raw):
    with pytest.raises(Exception):
        image_data_url(raw)
