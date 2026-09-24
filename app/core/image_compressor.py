"""Pure image encoding primitives."""
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image

class BaseCompressor(ABC):
    @abstractmethod
    async def compress(self, source: Path, output: Path): ...
    @abstractmethod
    def estimate_params(self, source: Path): ...
    @staticmethod
    def validate_output(output: Path) -> bool:
        return output.is_file() and output.stat().st_size > 0

class ImageCompressor(BaseCompressor):
    def estimate_params(self, source: Path):
        raise NotImplementedError("Parameter selection belongs to services.ai_service")

    async def compress(self, source: Path, output: Path, quality: int = 80):
        return await asyncio.to_thread(self._compress, source, output, quality)

    def _compress(self, source: Path, output: Path, quality: int):
        output.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            image.convert("RGB").save(output, "JPEG", quality=quality, optimize=True)
        return output
