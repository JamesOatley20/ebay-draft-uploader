"""Pure image boundary: original bytes in, one safe primary-still JPEG out.

No filesystem writes, network calls, external commands or software installation.
MPO/HEIF are still-photo containers, not animations merely because n_frames > 1.
"""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import warnings

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from . import AppError

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".mpo", ".png", ".webp", ".heic", ".heif"}
UNSUPPORTED_PHOTO_EXTENSIONS = {".tif", ".tiff", ".gif", ".bmp", ".dng", ".raw", ".avif"}
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 80_000_000
MAX_OUTPUT_SIDE = 4096
MIN_LONG_SIDE = 500


@dataclass(frozen=True)
class Photo:
    """name refers to the ORIGINAL; content/digest refer to the JPEG derivative."""

    name: str
    content: bytes
    digest: str
    width: int
    height: int
    source_format: str = ""
    source_frames: int = 1
    selected_frame: int = 0
    source_size: tuple[int, int] = (0, 0)
    notes: tuple[str, ...] = ()



class DecoderUnavailable(AppError):
    """A missing environment capability, not a claim that the photograph is invalid."""


def _heif_decoder() -> None:
    """Enable HEIC/HEIF support when a photo needs it."""
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener(thumbnails=False)
    except (ImportError, OSError) as exc:
        raise DecoderUnavailable(
            "HEIC/HEIF support is missing. Run Setup.cmd again; your original photo is unchanged."
        ) from exc


def _size_check(image: Image.Image) -> None:
    if image.width < 1 or image.height < 1 or image.width * image.height > MAX_PIXELS:
        raise AppError("Photo exceeds the application's 80 megapixel safety limit.")
    if max(image.size) < MIN_LONG_SIDE:
        raise AppError("Photo's longest side must be at least 500 pixels; it will not be upscaled.")


def _clean_rgb(image: Image.Image, notes: list[str]) -> Image.Image:
    """Apply available ICC colour information, flatten alpha, discard private tags."""
    alpha = None
    if "A" in image.getbands() or "transparency" in image.info:
        alpha = image.convert("RGBA").getchannel("A")
    profile = image.info.get("icc_profile")
    base = image if image.mode in {"RGB", "CMYK", "L", "LAB"} else image.convert("RGB")
    if profile:
        try:
            base = ImageCms.profileToProfile(
                base, ImageCms.ImageCmsProfile(BytesIO(profile)),
                ImageCms.createProfile("sRGB"), outputMode="RGB",
            )
            notes.append("Embedded ICC colours converted to sRGB.")
        except (ImageCms.PyCMSError, OSError, TypeError, ValueError):
            base = image.convert("RGB")
            notes.append("ICC profile could not be applied; check colour in the JPEG preview.")
    else:
        base = image.convert("RGB")
        if image.mode not in {"RGB", "RGBA", "L", "LA", "P", "1"}:
            notes.append("No usable ICC profile for this colour mode; check the JPEG preview.")
    # New pixel buffer drops EXIF, XMP, IPTC, comments, gain maps and other tags.
    clean = Image.new("RGB", base.size, "white")
    clean.paste(base, mask=alpha)
    if alpha is not None:
        notes.append("Transparency composited on white.")
    return clean


def _encode_jpeg(image: Image.Image, notes: list[str]) -> tuple[bytes, tuple[int, int]]:
    """Bound only the derivative, preserving aspect ratio and never cropping."""
    source_size = image.size
    image.thumbnail((MAX_OUTPUT_SIDE, MAX_OUTPUT_SIDE), Image.Resampling.LANCZOS)
    if image.size != source_size:
        notes.append("JPEG copy reduced to a maximum 4096-pixel long edge; original retained.")
    # Bounded fallback for unusually noisy/large photographs; no manual resize step.
    for attempt in range(12):
        for quality in (95, 90, 85):
            output = BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True,
                       exif=b"", icc_profile=None)
            encoded = output.getvalue()
            if len(encoded) <= MAX_UPLOAD_BYTES:
                if quality != 95 or attempt:
                    notes.append(f"JPEG fitted automatically to the 12 MiB limit (quality {quality}).")
                return encoded, image.size
        if max(image.size) <= MIN_LONG_SIDE:
            break
        edge = max(MIN_LONG_SIDE, int(max(image.size) * 0.8))
        image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    raise AppError("Cannot make a JPEG within the upload limit without going below 500 pixels.")


def normalize_photo(content: bytes, name: str) -> Photo:
    """Decode by content, select the primary still and return a JPEG snapshot.

    MPO starts on its primary frame. pillow-heif opens at its primary_index,
    which need not be zero: DO NOT seek(0) for HEIF. Additional container frames
    remain in the original; they are not separately listed or presumed to be HDR.
    """
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_SOURCE_BYTES:
        raise AppError(f"{name}: photo must be non-empty and no larger than 64 MiB.")
    # HEIF is an ISO base-media container. Check content, not a .JPEG/.HEIC suffix.
    # Pillow recognises MPO through its JPEG factory, not an MPO open factory.
    formats = ["JPEG", "PNG", "WEBP"]
    if content[4:8] == b"ftyp":
        _heif_decoder()
        formats.append("HEIF")
    notes: list[str] = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content), formats=formats) as original:
                source_format = original.format or ""
                if source_format not in {"JPEG", "MPO", "PNG", "WEBP", "HEIF"}:
                    raise AppError(f"{name}: unsupported image content.")
                frames = getattr(original, "n_frames", 1)
                selected = original.tell()
                if not 1 <= frames <= 256 or not 0 <= selected < frames:
                    raise AppError(f"{name}: invalid or excessive image-container frame count.")
                if source_format not in {"MPO", "HEIF"} and frames != 1:
                    raise AppError(f"{name}: animated PNG/WEBP is not a still photograph.")
                _size_check(original)  # Before decoding, including large HEIF inputs.
                original.load()
                _size_check(original)  # Some decoders finalise dimensions during load.
                source_size = original.size
                if source_format in {"MPO", "HEIF"}:
                    notes.append(f"{source_format}: primary still (frame {selected}) used; "
                                 f"{frames} reported container frame(s). Original retained.")
                if source_format == "HEIF":
                    notes.append("HEIF decoded to 8-bit JPEG; HDR rendering may differ. Check colours/brightness.")
                if original.getexif().get(274, 1) != 1:
                    notes.append("EXIF orientation applied before removing metadata.")
                oriented = ImageOps.exif_transpose(original)
                clean = _clean_rgb(oriented, notes)
                try:
                    encoded, size = _encode_jpeg(clean, notes)
                finally:
                    clean.close()
                    oriented.close()
    except AppError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError,
            RuntimeError, KeyError, IndexError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise AppError(f"{name}: cannot decode the primary photograph safely; original retained.") from exc
    return Photo(name, encoded, sha256(encoded).hexdigest(), *size,
                 source_format, frames, selected, source_size, tuple(notes))
