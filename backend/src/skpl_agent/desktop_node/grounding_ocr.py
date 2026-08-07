"""OCR grounding — text detection and recognition from screenshots.

Provides OCR-based grounding for detecting text elements in desktop
screenshots. Supports multiple OCR backends:
- easyocr: General-purpose OCR with good accuracy, GPU-friendly
- paddleocr: High-accuracy OCR with Chinese/English support

Uses lazy imports to avoid crashing when OCR dependencies are not installed.
"""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OCRResult:
    """Result of OCR text detection.

    Attributes:
        text_regions: List of detected text regions with bounding boxes.
        full_text: Concatenated text from all detected regions.
        backend: Name of the OCR backend used.
        latency_ms: OCR processing time in milliseconds.
    """

    def __init__(
        self,
        text_regions: list[dict[str, Any]],
        full_text: str = "",
        backend: str = "",
        latency_ms: float = 0.0,
    ) -> None:
        self.text_regions = text_regions
        self.full_text = full_text
        self.backend = backend
        self.latency_ms = latency_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a plain dict."""
        return {
            "text_regions": self.text_regions,
            "full_text": self.full_text,
            "backend": self.backend,
            "latency_ms": self.latency_ms,
        }

    def get_text_at_position(self, x: int, y: int) -> str | None:
        """Get text at a specific screen position.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Text at the position, or None if no text found.
        """
        for region in self.text_regions:
            bbox = region.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return region.get("text", "")
        return None

    def find_text_position(self, text: str, case_sensitive: bool = False) -> tuple[int, int] | None:
        """Find the center position of a text region.

        Args:
            text: Text to search for.
            case_sensitive: Whether to match case-sensitively.

        Returns:
            (x, y) center of the matching text region, or None.
        """
        search_text = text if case_sensitive else text.lower()
        for region in self.text_regions:
            region_text = region.get("text", "")
            if not case_sensitive:
                region_text = region_text.lower()
            if search_text in region_text:
                bbox = region.get("bbox", [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    return (int((x1 + x2) / 2), int((y1 + y2) / 2))
        return None


class OCRGrounding:
    """OCR-based text grounding from screenshots.

    Detects text regions in screenshots using OCR, providing bounding
    boxes and text content for each detected region. This is useful for
    finding text elements that may not be in the accessibility tree.

    Supports multiple OCR backends:
    - easyocr: Multi-language OCR, works well on GPU
    - paddleocr: High accuracy for Chinese+English, works on CPU/GPU

    Usage:
        >>> ocr = OCRGrounding(backend="easyocr")
        >>> ocr.load()
        >>> result = ocr.extract_text(screenshot_bytes)
        >>> for region in result.text_regions:
        ...     print(region["text"], region["bbox"])
    """

    AVAILABLE_BACKENDS = ("easyocr", "paddleocr")

    def __init__(
        self,
        backend: str = "easyocr",
        languages: list[str] | None = None,
        confidence_threshold: float = 0.5,
        use_gpu: bool = False,
    ) -> None:
        if backend not in self.AVAILABLE_BACKENDS:
            raise ValueError(
                f"Unknown OCR backend: {backend}. "
                f"Available: {self.AVAILABLE_BACKENDS}"
            )
        self._backend = backend
        self._languages = languages or ["en", "ch_sim"]
        self._confidence_threshold = confidence_threshold
        self._use_gpu = use_gpu
        self._loaded = False
        self._reader: Any = None

    @property
    def backend(self) -> str:
        """Return the OCR backend name."""
        return self._backend

    @property
    def is_loaded(self) -> bool:
        """Return whether the OCR engine is loaded."""
        return self._loaded

    @property
    def confidence_threshold(self) -> float:
        """Return the confidence threshold."""
        return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        self._confidence_threshold = value

    def load(self) -> None:
        """Load the OCR engine into memory.

        Raises:
            ImportError: If the OCR backend is not installed.
            RuntimeError: If the OCR engine fails to load.
        """
        if self._loaded:
            return

        if self._backend == "easyocr":
            self._load_easyocr()
        elif self._backend == "paddleocr":
            self._load_paddleocr()

        self._loaded = True

    def _load_easyocr(self) -> None:
        """Load the easyocr reader."""
        try:
            import easyocr

            logger.info(
                "Loading easyocr with languages: %s, GPU: %s",
                self._languages, self._use_gpu,
            )
            self._reader = easyocr.Reader(
                self._languages,
                gpu=self._use_gpu,
            )
            logger.info("easyocr loaded successfully")

        except ImportError as e:
            raise ImportError(
                "easyocr not installed. Install with: pip install easyocr opencv-python-headless"
            ) from e
        except Exception as e:
            logger.error("Failed to load easyocr: %s", e)
            raise RuntimeError(f"Failed to load easyocr: {e}") from e

    def _load_paddleocr(self) -> None:
        """Load the paddleocr engine."""
        try:
            from paddleocr import PaddleOCR

            logger.info("Loading PaddleOCR...")
            lang = "ch" if "ch" in self._languages else "en"
            self._reader = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                use_gpu=self._use_gpu,
                show_log=False,
            )
            logger.info("PaddleOCR loaded successfully")

        except ImportError as e:
            raise ImportError(
                "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
            ) from e
        except Exception as e:
            logger.error("Failed to load PaddleOCR: %s", e)
            raise RuntimeError(f"Failed to load PaddleOCR: {e}") from e

    def unload(self) -> None:
        """Unload the OCR engine to free memory."""
        self._reader = None
        self._loaded = False
        logger.info("OCR engine unloaded")

    def extract_text(
        self,
        screenshot: bytes,
        detail_level: str = "normal",
    ) -> OCRResult:
        """Extract all text regions from a screenshot.

        Args:
            screenshot: Raw screenshot bytes (JPEG or PNG).
            detail_level: "normal" or "detailed" (includes confidence per char).

        Returns:
            OCRResult with detected text regions.
        """
        if not self._loaded:
            self.load()

        start = time.monotonic()

        try:
            from PIL import Image

            image = Image.open(io.BytesIO(screenshot)).convert("RGB")

            if self._backend == "easyocr":
                text_regions = self._extract_easyocr(image)
            elif self._backend == "paddleocr":
                text_regions = self._extract_paddleocr(image)
            else:
                text_regions = []

            full_text = " ".join(
                r.get("text", "") for r in text_regions
            )

            latency = (time.monotonic() - start) * 1000

            logger.info(
                "OCR detected %d text regions in %.1fms",
                len(text_regions), latency,
            )

            return OCRResult(
                text_regions=text_regions,
                full_text=full_text,
                backend=self._backend,
                latency_ms=round(latency, 2),
            )

        except Exception as e:
            logger.error("OCR extraction failed: %s", e)
            latency = (time.monotonic() - start) * 1000
            return OCRResult(
                text_regions=[],
                backend=self._backend,
                latency_ms=round(latency, 2),
            )

    def find_text(
        self,
        screenshot: bytes,
        text: str,
        case_sensitive: bool = False,
    ) -> dict[str, Any] | None:
        """Find a specific text on the screen.

        Args:
            screenshot: Raw screenshot bytes.
            text: Text to search for.
            case_sensitive: Whether to match case-sensitively.

        Returns:
            Dict with bbox, center, and confidence, or None if not found.
        """
        result = self.extract_text(screenshot)
        position = result.find_text_position(text, case_sensitive=case_sensitive)
        if position is None:
            return None

        # Find the matching region for additional info
        search_text = text if case_sensitive else text.lower()
        for region in result.text_regions:
            region_text = region.get("text", "")
            if not case_sensitive:
                region_text = region_text.lower()
            if search_text in region_text:
                bbox = region.get("bbox", [])
                return {
                    "text": region.get("text", ""),
                    "bbox": bbox,
                    "center": list(position),
                    "confidence": region.get("confidence", 0.0),
                }

        return None

    def _extract_easyocr(self, image: Any) -> list[dict[str, Any]]:
        """Extract text using easyocr.

        Args:
            image: PIL Image.

        Returns:
            List of text region dicts.
        """
        import numpy as np

        image_np = np.array(image)
        results = self._reader.readtext(image_np)

        text_regions: list[dict[str, Any]] = []
        for i, (bbox, text, confidence) in enumerate(results):
            if confidence < self._confidence_threshold:
                continue

            # Convert bbox from polygon to rectangle
            if len(bbox) == 4:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x1, y1 = int(min(xs)), int(min(ys))
                x2, y2 = int(max(xs)), int(max(ys))
            else:
                continue

            text_regions.append({
                "index": i,
                "text": text,
                "bbox": [x1, y1, x2, y2],
                "confidence": float(confidence),
                "type": "text",
            })

        return text_regions

    def _extract_paddleocr(self, image: Any) -> list[dict[str, Any]]:
        """Extract text using PaddleOCR.

        Args:
            image: PIL Image.

        Returns:
            List of text region dicts.
        """
        import numpy as np

        image_np = np.array(image)
        results = self._reader.ocr(image_np, cls=True)

        if not results or not results[0]:
            return []

        text_regions: list[dict[str, Any]] = []
        for i, line in enumerate(results[0]):
            if line is None:
                continue
            bbox, (text, confidence) = line
            if confidence < self._confidence_threshold:
                continue

            if len(bbox) == 4:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x1, y1 = int(min(xs)), int(min(ys))
                x2, y2 = int(max(xs)), int(max(ys))
            else:
                continue

            text_regions.append({
                "index": i,
                "text": text,
                "bbox": [x1, y1, x2, y2],
                "confidence": float(confidence),
                "type": "text",
            })

        return text_regions

    def extract_text_from_base64(
        self,
        image_base64: str,
    ) -> OCRResult:
        """Extract text from a base64-encoded screenshot.

        Args:
            image_base64: Base64-encoded image string.

        Returns:
            OCRResult with detected text regions.
        """
        screenshot = base64.b64decode(image_base64)
        return self.extract_text(screenshot)

    def find_text_from_base64(
        self,
        image_base64: str,
        text: str,
        case_sensitive: bool = False,
    ) -> dict[str, Any] | None:
        """Find text in a base64-encoded screenshot.

        Args:
            image_base64: Base64-encoded image string.
            text: Text to search for.
            case_sensitive: Whether to match case-sensitively.

        Returns:
            Dict with bbox and center, or None.
        """
        screenshot = base64.b64decode(image_base64)
        return self.find_text(screenshot, text, case_sensitive=case_sensitive)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_ocr_grounding(
    backend: str = "easyocr",
    languages: list[str] | None = None,
    confidence_threshold: float = 0.5,
    use_gpu: bool = False,
    **kwargs: Any,
) -> OCRGrounding:
    """Create an OCR grounding instance.

    Args:
        backend: OCR backend ("easyocr" or "paddleocr").
        languages: List of language codes (e.g., ["en", "ch_sim"]).
        confidence_threshold: Minimum confidence for text detection.
        use_gpu: Whether to use GPU acceleration.
        **kwargs: Additional keyword arguments.

    Returns:
        OCRGrounding instance.
    """
    return OCRGrounding(
        backend=backend,
        languages=languages,
        confidence_threshold=confidence_threshold,
        use_gpu=use_gpu,
    )