import os
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from hylyre import image_io
from tests.image_samples import gray16_png_bytes, image_bytes, invalid_images


@pytest.mark.parametrize("source", ["JPEG", "PNG"])
@pytest.mark.parametrize("suffix", [".png", ".jpg", ".jpeg", ".PNG", ".JpG", ".JPEG"])
def test_format_content_and_requested_path(tmp_path, source, suffix):
    raw = image_bytes(source)
    out = tmp_path / ("shot" + suffix)
    assert image_io.write_image(raw, out) == str(out.resolve())
    expected = "PNG" if suffix.lower() == ".png" else "JPEG"
    assert image_io.image_mime(out.read_bytes()) == "image/" + expected.lower()
    with Image.open(out) as actual, Image.open(BytesIO(raw)) as original:
        actual.load()
        original.load()
        assert actual.format == expected
        assert actual.size == original.size == (48, 32)
        if source == expected:
            assert out.read_bytes() == raw
        elif expected == "PNG":
            assert actual.tobytes() == original.tobytes()
        else:
            # Sample well inside each block; JPEG quality=95, per-channel error <=12.
            for point in [(8, 8), (36, 24), (36, 8)]:
                assert max(abs(a-b) for a,b in zip(actual.getpixel(point), original.getpixel(point))) <= 12


def test_alpha_is_composited_on_white(tmp_path):
    out = tmp_path / "alpha.jpg"
    image_io.write_image(image_bytes(alpha=True), out)
    with Image.open(out) as image:
        for point, expected in [((8, 8), (237, 142, 147)), ((36, 8), (255, 255, 255)), ((36, 24), (20, 80, 220))]:
            assert max(abs(a-b) for a,b in zip(image.getpixel(point), expected)) <= 12


def test_cmyk_jpeg_to_png(tmp_path):
    stream = BytesIO()
    with Image.open(BytesIO(image_bytes())) as source:
        source.convert("CMYK").save(stream, format="JPEG", quality=95)
    raw = stream.getvalue()
    out = tmp_path / "cmyk.png"
    image_io.write_image(raw, out)
    assert image_io.image_mime(out.read_bytes()) == "image/png"
    with Image.open(out) as actual, Image.open(BytesIO(raw)) as original:
        actual.load()
        original.load()
        assert actual.size == original.size
        assert actual.tobytes() == original.convert("RGB").tobytes()


def test_gray16_png_uses_fixed_full_range_for_jpeg(tmp_path):
    raw = gray16_png_bytes()
    with Image.open(BytesIO(raw)) as source:
        source.load()
        assert source.getextrema() == (4096, 49152)
    png = tmp_path / "gray16.png"
    image_io.write_image(raw, png)
    assert png.read_bytes() == raw
    out = tmp_path / "gray16.jpg"
    image_io.write_image(raw, out)
    with Image.open(out) as image:
        image.load()
        assert image.format == "JPEG"
        assert image.size == (64, 16)
        for x, expected in [(8, 16), (24, 64), (40, 128), (56, 191)]:
            assert all(abs(value - expected) <= 2 for value in image.getpixel((x, 8)))


@pytest.mark.parametrize("raw", invalid_images())
def test_bad_images_never_publish(tmp_path, raw):
    with pytest.raises(ValueError, match="Screenshot is not a valid PNG/JPEG image:") as failure:
        image_io.image_mime(raw)
    assert failure.value.__cause__ is not None
    assert str(failure.value.__cause__) in str(failure.value)
    out = tmp_path / "shot.png"
    with pytest.raises(Exception):
        image_io.write_image(raw, out)
    assert not out.exists()
    old = image_bytes()
    out.write_bytes(old)
    with pytest.raises(Exception):
        image_io.write_image(raw, out)
    assert out.read_bytes() == old
    assert list(tmp_path.iterdir()) == [out]


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", ["encode", "write", "close", "replace"])
def test_publication_failures_keep_target_and_clean_temp(tmp_path, monkeypatch, existing, failure):
    out = tmp_path / "shot.jpg"
    old = image_bytes("JPEG")
    if existing:
        out.write_bytes(old)

    def fail(*args, **kwargs):
        raise OSError("injected " + failure)

    if failure == "encode":
        monkeypatch.setattr(Image.Image, "save", fail)
    elif failure == "replace":
        monkeypatch.setattr(image_io.os, "replace", fail)
    else:
        factory = image_io.NamedTemporaryFile

        class Stream:
            def __enter__(self):
                self.stream = factory(dir=tmp_path, delete=False)
                self.name = self.stream.name
                return self

            def write(self, raw):
                self.stream.write(raw[:5])
                if failure == "write":
                    fail()
                return self.stream.write(raw[5:])

            def __exit__(self, *args):
                self.stream.close()
                if failure == "close":
                    fail()

        monkeypatch.setattr(image_io, "NamedTemporaryFile", lambda **kwargs: Stream())
    with pytest.raises(OSError, match="injected"):
        image_io.write_image(old if failure in ("write", "close") else image_bytes(), out)
    assert out.exists() == existing
    if existing:
        assert out.read_bytes() == old
    assert list(tmp_path.iterdir()) == ([out] if existing else [])


def test_missing_pillow_is_lazy_and_observable(tmp_path, monkeypatch):
    import builtins

    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "PIL":
            raise ImportError("Pillow is unavailable")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(ImportError, match="Pillow"):
        image_io.write_image(image_bytes(), tmp_path / "shot.png")


def _mpo_bytes():
    stream = BytesIO()
    with Image.open(BytesIO(image_bytes("JPEG"))) as first:
        first.save(stream, format="MPO", save_all=True, append_images=[Image.new("RGB", first.size, "blue")])
    return stream.getvalue()


def test_mpo_jpeg_is_accepted_as_jpeg(tmp_path):
    raw = _mpo_bytes()
    with Image.open(BytesIO(raw)) as probe:
        assert probe.format == "MPO"  # Pillow's name for a JPEG with an MPF segment
    assert image_io.image_mime(raw) == "image/jpeg"
    jpg = tmp_path / "shot.jpg"
    image_io.write_image(raw, jpg)
    assert jpg.read_bytes() == raw
    png = tmp_path / "shot.png"
    image_io.write_image(raw, png)
    with Image.open(png) as actual, Image.open(BytesIO(raw)) as original:
        assert actual.format == "PNG"
        assert actual.tobytes() == original.convert("RGB").tobytes()


def test_published_file_mode_follows_umask(tmp_path, monkeypatch):
    modes = []
    chmod = image_io.os.chmod
    monkeypatch.setattr(image_io.os, "chmod", lambda path, mode: (modes.append(mode), chmod(path, mode)))
    out = tmp_path / "shot.png"
    image_io.write_image(image_bytes(), out)
    assert modes == [0o666 & ~image_io._UMASK]
    if os.name == "posix":
        assert out.stat().st_mode & 0o777 == 0o666 & ~image_io._UMASK
