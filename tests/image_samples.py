"""Small real images with spatial content, shared by offline acceptance tests."""

from io import BytesIO

from PIL import Image, ImageDraw


def image_bytes(format="PNG", *, alpha=False):
    image = Image.new("RGBA" if alpha else "RGB", (48, 32), (0, 0, 0, 0) if alpha else "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 23, 15), fill=(220, 30, 40, 128) if alpha else (220, 30, 40))
    draw.rectangle((24, 16, 47, 31), fill=(20, 80, 220, 255) if alpha else (20, 80, 220))
    stream = BytesIO()
    image.save(stream, format=format, quality=95)
    return stream.getvalue()


def png_bytes():
    return image_bytes()


def gray16_png_bytes():
    image = Image.new("I;16", (64, 16))
    image.putdata([4096 if x < 16 else 16384 if x < 32 else 32768 if x < 48 else 49152 for y in range(16) for x in range(64)])
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def invalid_images():
    png = bytearray(png_bytes())
    idat = png.index(b"IDAT")
    png[idat + 5] ^= 1  # Keep the PNG signature; break the IDAT CRC.
    return [b"", b"not an image", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff\xe0", bytes(png), png_bytes()[:45], image_bytes("JPEG")[:-30]]
