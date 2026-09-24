"""Pure JPEG encoding primitives.

This module performs one encoding pass only. Parameter prediction, quality
evaluation, and retry/adjustment decisions belong to ``services.ai_service``;
keeping them out of this class makes the encoder reusable for both adaptive
compression and fixed-quality comparisons.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image, ImageOps


class BaseCompressor(ABC):
    """Contract for asynchronous media encoders."""

    @abstractmethod
    async def compress(self, source: Path, output: Path, quality: int = 80) -> Path:
        """Encode ``source`` into ``output`` and return the output path."""

    @staticmethod
    def validate_output(output: Path) -> bool:
        """Return whether an encoder produced a non-empty regular file."""
        return output.is_file() and output.stat().st_size > 0


class ImageCompressor(BaseCompressor):
    """Encode an image as an optimized RGB JPEG in a worker thread."""

    async def compress(self, source: Path, output: Path, quality: int = 80) -> Path:
        """Run the blocking Pillow operation without blocking the event loop.

        Pillow is synchronous, while the API workers are asynchronous. Moving
        the actual encode to a thread keeps other requests responsive. Quality
        validation happens before scheduling work so invalid requests fail
        immediately and consistently.
        """
        self._validate_quality(quality)
        return await asyncio.to_thread(self._compress, source, output, quality)

    @staticmethod
    def _validate_quality(quality: int) -> None:
        """Validate Pillow's JPEG quality range."""
        if isinstance(quality, bool) or not isinstance(quality, int):
            raise TypeError("quality must be an integer")
        if not 1 <= quality <= 100:
            raise ValueError("quality must be between 1 and 100")

    def _compress(self, source: Path, output: Path, quality: int) -> Path:
        """Perform one safe, atomic JPEG encode.

        The temporary file prevents callers from observing a partially written
        result if Pillow fails. ``exif_transpose`` applies camera orientation
        metadata before pixels are saved, avoiding sideways phone photos. The
        explicit RGB conversion removes palette, grayscale, and alpha-channel
        incompatibilities with JPEG.
        """
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.tmp")
        try:
            with Image.open(source) as image:
                oriented = ImageOps.exif_transpose(image).convert("RGB")
                oriented.save(temporary, format="JPEG", quality=quality, optimize=True)
            if not self.validate_output(temporary):
                raise OSError("JPEG encoder produced an empty output")
            temporary.replace(output)
            return output
        finally:
            # Cleanup is safe after replace (the temporary path no longer
            # exists) and also covers failures during image decoding or save.
            temporary.unlink(missing_ok=True)
