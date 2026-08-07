"""UI-TARS model grounding — visual grounding via transformer-based model.

Implements grounding of UI elements using the UI-TARS model
(https://github.com/bytedance/UI-TARS), a vision-language model
specifically designed for GUI understanding and grounding tasks.

The model detects UI elements from screenshots and returns bounding
boxes, labels, and confidence scores. This module uses lazy imports
to avoid crashing when transformers/torch are not installed.
"""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UI_TARS_GroundingResult:
    """Result of a UI-TARS grounding operation.

    Attributes:
        elements: List of detected UI elements with bounding boxes and labels.
        annotated_image_base64: Base64-encoded annotated screenshot.
        instruction: The original grounding instruction.
        model_used: Name of the model used.
        latency_ms: Grounding latency in milliseconds.
    """

    def __init__(
        self,
        elements: list[dict[str, Any]],
        annotated_image_base64: str = "",
        instruction: str = "",
        model_used: str = "ui-tars",
        latency_ms: float = 0.0,
    ) -> None:
        self.elements = elements
        self.annotated_image_base64 = annotated_image_base64
        self.instruction = instruction
        self.model_used = model_used
        self.latency_ms = latency_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a plain dict."""
        return {
            "elements": self.elements,
            "annotated_image_base64": self.annotated_image_base64,
            "instruction": self.instruction,
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
        }

    def get_center_element(self) -> dict[str, Any] | None:
        """Return the highest-confidence element."""
        if not self.elements:
            return None
        return max(self.elements, key=lambda e: e.get("confidence", 0.0))

    def get_element_by_label(self, label: str) -> dict[str, Any] | None:
        """Find an element by its label (case-insensitive)."""
        label_lower = label.lower()
        for elem in self.elements:
            if label_lower in elem.get("label", "").lower():
                return elem
        return None

    def get_click_point(self, element_index: int = 0) -> tuple[int, int] | None:
        """Get the center click point for an element."""
        if element_index >= len(self.elements):
            return None
        elem = self.elements[element_index]
        bbox = elem.get("bbox", [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            return (int((x1 + x2) / 2), int((y1 + y2) / 2))
        return None


class UI_TARS_Grounding:
    """UI-TARS grounding model for detecting UI elements in screenshots.

    UI-TARS is a vision-language model trained specifically for GUI
    understanding and grounding tasks. It can detect interactive elements
    such as buttons, text fields, icons, and links from screenshots.

    The model is loaded lazily via HuggingFace transformers to avoid
    dependency issues when the model is not needed.

    Usage:
        >>> grounding = UI_TARS_Grounding(
        ...     model_name="bytedance/UI-TARS",
        ...     device="cpu",
        ... )
        >>> grounding.load()
        >>> result = grounding.detect_elements(screenshot_bytes)
        >>> for elem in result.elements:
        ...     print(elem["label"], elem["bbox"])
    """

    DEFAULT_MODEL = "bytedance/UI-TARS"

    def __init__(
        self,
        model_name: str = "",
        device: str = "cpu",
        confidence_threshold: float = 0.3,
        max_elements: int = 100,
    ) -> None:
        self._model_name = model_name or self.DEFAULT_MODEL
        self._device = device
        self._confidence_threshold = confidence_threshold
        self._max_elements = max_elements
        self._loaded = False
        self._model: Any = None
        self._processor: Any = None

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        """Return whether the model is loaded."""
        return self._loaded

    @property
    def confidence_threshold(self) -> float:
        """Return the confidence threshold."""
        return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        """Set the confidence threshold (0.0 to 1.0)."""
        if not 0.0 <= value <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        self._confidence_threshold = value

    def load(self) -> None:
        """Load the UI-TARS model and processor.

        Uses lazy imports to avoid dependency issues when the model
        is not installed.

        Raises:
            ImportError: If transformers or torch are not installed.
            RuntimeError: If the model fails to load.
        """
        if self._loaded:
            return

        try:
            import torch
            from transformers import AutoModel, AutoProcessor

            logger.info(
                "Loading UI-TARS model: %s on %s",
                self._model_name, self._device,
            )

            self._processor = AutoProcessor.from_pretrained(
                self._model_name,
                trust_remote_code=True,
            )

            self._model = AutoModel.from_pretrained(
                self._model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
            ).to(self._device)

            self._model.eval()
            self._loaded = True

            logger.info("UI-TARS model loaded successfully on %s", self._device)

        except ImportError as e:
            logger.warning(
                "transformers/torch not available. UI-TARS grounding will not work. "
                "Install with: pip install transformers torch"
            )
            raise ImportError(
                "UI-TARS grounding requires transformers and torch. "
                "Install with: pip install transformers torch"
            ) from e
        except Exception as e:
            logger.error("Failed to load UI-TARS model: %s", e)
            raise RuntimeError(f"Failed to load UI-TARS model: {e}") from e

    def unload(self) -> None:
        """Unload the model to free GPU/CPU memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        self._loaded = False
        logger.info("UI-TARS model unloaded")

    def detect_elements(
        self,
        screenshot: bytes,
        instruction: str = "",
        img_format: str = "jpeg",
    ) -> UI_TARS_GroundingResult:
        """Detect UI elements from a screenshot.

        Args:
            screenshot: Raw screenshot bytes (JPEG or PNG).
            instruction: Optional natural language instruction for targeted detection.
            img_format: Image format of the screenshot (jpeg/png).

        Returns:
            UI_TARS_GroundingResult with detected elements.
        """
        if not self._loaded:
            self.load()

        start = time.monotonic()

        try:
            from PIL import Image

            # Decode screenshot to PIL Image
            image = Image.open(io.BytesIO(screenshot)).convert("RGB")
            img_w, img_h = image.size

            # Build prompt
            prompt = self._build_prompt(instruction)

            # Run inference
            elements = self._run_inference(image, prompt, img_w, img_h)

            # Annotate image with bounding boxes
            annotated_b64 = self._annotate_image(image, elements)

            latency = (time.monotonic() - start) * 1000

            logger.info(
                "UI-TARS detected %d elements in %.1fms",
                len(elements), latency,
            )

            return UI_TARS_GroundingResult(
                elements=elements,
                annotated_image_base64=annotated_b64,
                instruction=instruction,
                model_used=self._model_name,
                latency_ms=round(latency, 2),
            )

        except Exception as e:
            logger.error("UI-TARS grounding failed: %s", e)
            latency = (time.monotonic() - start) * 1000
            return UI_TARS_GroundingResult(
                elements=[],
                instruction=instruction,
                model_used=self._model_name,
                latency_ms=round(latency, 2),
            )

    def _build_prompt(self, instruction: str) -> str:
        """Build the model prompt from an instruction.

        Args:
            instruction: Natural language instruction.

        Returns:
            Formatted prompt string.
        """
        if instruction:
            return (
                f"Detect UI elements relevant to: {instruction}\n"
                "Return bounding boxes with labels and confidence scores."
            )
        else:
            return (
                "Detect all interactive UI elements in the screenshot. "
                "Include buttons, text fields, icons, links, checkboxes, "
                "radio buttons, dropdowns, sliders, and tabs. "
                "Return bounding boxes with labels and confidence scores."
            )

    def _run_inference(
        self,
        image: Any,
        prompt: str,
        img_w: int,
        img_h: int,
    ) -> list[dict[str, Any]]:
        """Run model inference on the image.

        Args:
            image: PIL Image.
            prompt: Text prompt for the model.
            img_w: Image width.
            img_h: Image height.

        Returns:
            List of detected element dicts.
        """
        try:
            import torch

            inputs = self._processor(
                images=image,
                text=prompt,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)

            return self._parse_outputs(outputs, img_w, img_h)

        except Exception as e:
            logger.error("Inference failed: %s", e)
            raise

    def _parse_outputs(
        self,
        outputs: Any,
        img_w: int,
        img_h: int,
    ) -> list[dict[str, Any]]:
        """Parse model outputs into structured element list.

        Attempts to handle multiple output formats:
        - Standard object detection format (boxes, labels, scores)
        - UI-TARS specific format
        - Text-based format (parsed from generated text)

        Args:
            outputs: Raw model outputs.
            img_w: Image width.
            img_h: Image height.

        Returns:
            List of element dicts with bbox, label, confidence.
        """
        elements: list[dict[str, Any]] = []

        try:
            # Try standard object detection format
            if hasattr(outputs, "boxes"):
                boxes = outputs.boxes
                labels = getattr(outputs, "labels", [f"element_{i}" for i in range(len(boxes))])
                scores = getattr(outputs, "scores", [1.0] * len(boxes))

                if hasattr(boxes, "cpu"):
                    boxes = boxes.cpu().numpy()
                if hasattr(scores, "cpu"):
                    scores = scores.cpu().numpy()

                for i, box in enumerate(boxes):
                    score = float(scores[i]) if i < len(scores) else 1.0
                    if score < self._confidence_threshold:
                        continue

                    x1, y1, x2, y2 = box[:4]
                    elements.append({
                        "index": i,
                        "label": str(labels[i]) if i < len(labels) else f"element_{i}",
                        "bbox": [
                            max(0, int(x1)),
                            max(0, int(y1)),
                            min(img_w, int(x2)),
                            min(img_h, int(y2)),
                        ],
                        "confidence": score,
                        "type": "ui_element",
                    })

                    if len(elements) >= self._max_elements:
                        break

                return elements

            # Try UI-TARS text output
            if hasattr(outputs, "text"):
                text_output = outputs.text
                if isinstance(text_output, list):
                    text_output = text_output[0] if text_output else ""
                return self._parse_text_output(str(text_output), img_w, img_h)

            # Try to get text from generated outputs
            if hasattr(outputs, "sequences"):
                decoded = self._processor.batch_decode(
                    outputs.sequences, skip_special_tokens=True
                )
                if decoded:
                    return self._parse_text_output(str(decoded[0]), img_w, img_h)

        except Exception as e:
            logger.warning("Failed to parse model outputs: %s", e)

        return elements

    def _parse_text_output(
        self,
        text: str,
        img_w: int,
        img_h: int,
    ) -> list[dict[str, Any]]:
        """Parse text-based model output into element list.

        Attempts to extract bounding box coordinates and labels from
        the model's textual output.

        Args:
            text: Raw text output from the model.
            img_w: Image width.
            img_h: Image height.

        Returns:
            List of element dicts.
        """
        elements: list[dict[str, Any]] = []
        import re

        # Pattern: <box>label: x1 y1 x2 y2</box> or similar
        # Also try: label (x1, y1, x2, y2) confidence
        bbox_pattern = re.compile(
            r'\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)\s*'
            r'(?:([\w\s]+))?\s*'
            r'(?:(\d+\.?\d*))?',
            re.IGNORECASE,
        )
        matches = bbox_pattern.findall(text)

        for i, match in enumerate(matches):
            if len(match) >= 4:
                x1, y1, x2, y2 = int(match[0]), int(match[1]), int(match[2]), int(match[3])
                label = match[4].strip() if len(match) > 4 and match[4] else f"element_{i}"
                confidence = float(match[5]) if len(match) > 5 and match[5] else 1.0

                if confidence < self._confidence_threshold:
                    continue

                elements.append({
                    "index": i,
                    "label": label,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": confidence,
                    "type": "ui_element",
                })

                if len(elements) >= self._max_elements:
                    break

        return elements

    def _annotate_image(
        self,
        image: Any,
        elements: list[dict[str, Any]],
    ) -> str:
        """Draw bounding boxes and labels on the image.

        Args:
            image: PIL Image.
            elements: List of element dicts with bbox and label.

        Returns:
            Base64-encoded annotated image string.
        """
        try:
            from PIL import ImageDraw, ImageFont

            annotated = image.copy()
            draw = ImageDraw.Draw(annotated)

            colors = [
                "#FF0000", "#00FF00", "#0000FF", "#FFA500", "#800080",
                "#00FFFF", "#FF00FF", "#008000", "#FFD700", "#A52A2A",
            ]

            for i, elem in enumerate(elements):
                color = colors[i % len(colors)]
                bbox = elem.get("bbox", [])
                if len(bbox) == 4:
                    draw.rectangle(bbox, outline=color, width=2)
                    label = elem.get("label", f"#{i}")
                    conf = elem.get("confidence", 0.0)
                    text = f"{label} ({conf:.2f})"

                    # Draw text with background
                    text_bbox = draw.textbbox((bbox[0], bbox[1] - 14), text)
                    draw.rectangle(
                        [text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2],
                        fill=color,
                    )
                    draw.text(
                        (bbox[0], bbox[1] - 14),
                        text,
                        fill="#FFFFFF",
                    )

            buf = io.BytesIO()
            annotated.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

        except Exception as e:
            logger.warning("Failed to annotate image: %s", e)
            return ""

    def detect_click_target(
        self,
        screenshot: bytes,
        target_description: str,
    ) -> dict[str, Any] | None:
        """Detect the best click target matching a description.

        Convenience method that combines detection and finding the
        best matching element.

        Args:
            screenshot: Raw screenshot bytes.
            target_description: Natural language description of the target.

        Returns:
            Element dict with bbox and click_point, or None if not found.
        """
        result = self.detect_elements(screenshot, instruction=target_description)
        if not result.elements:
            return None

        # Find the best element matching the description
        best = None
        best_score = 0.0
        desc_lower = target_description.lower()

        for elem in result.elements:
            label = elem.get("label", "").lower()
            confidence = elem.get("confidence", 0.0)

            # Simple keyword matching
            score = confidence
            desc_words = desc_lower.split()
            for word in desc_words:
                if word in label:
                    score += 0.2

            if score > best_score:
                best_score = score
                best = elem

        if best is not None:
            click_point = result.get_click_point(
                best.get("index", 0)
            )
            if click_point:
                best["click_point"] = list(click_point)

        return best


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_ui_tars_grounding(
    model_name: str = "",
    device: str = "cpu",
    confidence_threshold: float = 0.3,
    **kwargs: Any,
) -> UI_TARS_Grounding:
    """Create a UI-TARS grounding instance.

    Args:
        model_name: Model name (defaults to bytedance/UI-TARS).
        device: Device for inference (cpu/cuda/mps).
        confidence_threshold: Minimum confidence for detected elements.
        **kwargs: Additional keyword arguments.

    Returns:
        UI_TARS_Grounding instance.
    """
    return UI_TARS_Grounding(
        model_name=model_name,
        device=device,
        confidence_threshold=confidence_threshold,
    )