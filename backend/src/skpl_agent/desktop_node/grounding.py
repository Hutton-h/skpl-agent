"""UI element grounding — OmniParser-based visual grounding of UI elements.

Adapted from Agent-S gui_agents/s1/core/grounding.py.
Provides UI element detection and grounding from screenshots, mapping
natural language instructions to specific UI element coordinates.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GroundingResult:
    """Result of a UI grounding operation.

    Attributes:
        elements: List of grounded UI elements with coordinates and labels.
        annotated_image_base64: Base64-encoded annotated screenshot.
        instruction: The original grounding instruction.
        model_used: Name of the grounding model used.
        latency_ms: Grounding latency in milliseconds.
    """

    def __init__(
        self,
        elements: list[dict[str, Any]],
        annotated_image_base64: str = "",
        instruction: str = "",
        model_used: str = "",
        latency_ms: float = 0.0,
    ) -> None:
        self.elements = elements
        self.annotated_image_base64 = annotated_image_base64
        self.instruction = instruction
        self.model_used = model_used
        self.latency_ms = latency_ms

    def to_dict(self) -> dict[str, Any]:
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

    def get_click_point(
        self, element_index: int = 0
    ) -> tuple[int, int] | None:
        """Get the center click point for an element."""
        if element_index >= len(self.elements):
            return None
        elem = self.elements[element_index]
        bbox = elem.get("bbox", [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            return (int((x1 + x2) / 2), int((y1 + y2) / 2))
        return None


class GroundingModel:
    """Base class for UI grounding models.

    Subclasses implement specific grounding backends:
    - OmniParserGrounding: Microsoft OmniParser v2
    - LocalGrounding: Local model inference
    - RemoteGrounding: API-based grounding service
    """

    def __init__(self, model_name: str = "", device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device
        self._loaded = False

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        """Load the grounding model into memory."""
        raise NotImplementedError

    def unload(self) -> None:
        """Unload the model to free memory."""
        raise NotImplementedError

    def ground(
        self,
        image_base64: str,
        instruction: str = "",
    ) -> GroundingResult:
        """Ground UI elements in an image based on an instruction.

        Args:
            image_base64: Base64-encoded screenshot.
            instruction: Natural language instruction (e.g., "click the submit button").

        Returns:
            GroundingResult with detected elements.
        """
        raise NotImplementedError


class OmniParserGrounding(GroundingModel):
    """Microsoft OmniParser v2 grounding model.

    OmniParser is a vision-language model that detects UI elements
    and their functions from screenshots. It outputs bounding boxes
    with labels and confidence scores.

    Reference: https://github.com/microsoft/OmniParser
    """

    def __init__(
        self,
        model_name: str = "microsoft/OmniParser-v2",
        device: str = "cpu",
    ) -> None:
        super().__init__(model_name=model_name, device=device)
        self._model: Any = None
        self._processor: Any = None

    def load(self) -> None:
        """Load OmniParser model and processor."""
        if self._loaded:
            return

        try:
            import torch
            from transformers import AutoModel, AutoProcessor

            logger.info(
                "Loading OmniParser model: %s on %s",
                self._model_name, self._device,
            )

            self._model = AutoModel.from_pretrained(
                self._model_name,
                trust_remote_code=True,
            ).to(self._device)
            self._processor = AutoProcessor.from_pretrained(
                self._model_name,
                trust_remote_code=True,
            )
            self._model.eval()
            self._loaded = True
            logger.info("OmniParser model loaded successfully")

        except ImportError:
            logger.warning(
                "transformers/torch not available. "
                "OmniParser grounding will not be available."
            )
            raise
        except Exception as e:
            logger.error("Failed to load OmniParser model: %s", e)
            raise

    def unload(self) -> None:
        """Unload model to free GPU/CPU memory."""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        self._loaded = False
        logger.info("OmniParser model unloaded")

    def ground(
        self,
        image_base64: str,
        instruction: str = "",
    ) -> GroundingResult:
        """Run OmniParser grounding on the image."""
        import time

        if not self._loaded:
            self.load()

        start = time.time()

        try:
            from PIL import Image

            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")

            # Run inference
            with self._get_device_context():
                inputs = self._processor(
                    images=image,
                    text=instruction or "detect all UI elements",
                    return_tensors="pt",
                )
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

                with self._get_no_grad():
                    outputs = self._model(**inputs)

            # Parse outputs into elements
            elements = self._parse_outputs(outputs, image.size)

            # Optionally annotate the image
            annotated_b64 = self._annotate_image(image, elements)

            latency = (time.time() - start) * 1000

            return GroundingResult(
                elements=elements,
                annotated_image_base64=annotated_b64,
                instruction=instruction,
                model_used=self._model_name,
                latency_ms=round(latency, 2),
            )

        except Exception as e:
            logger.error("OmniParser grounding failed: %s", e)
            latency = (time.time() - start) * 1000
            return GroundingResult(
                elements=[],
                instruction=instruction,
                model_used=self._model_name,
                latency_ms=round(latency, 2),
            )

    def _parse_outputs(
        self, outputs: Any, image_size: tuple[int, int]
    ) -> list[dict[str, Any]]:
        """Parse model outputs into structured element list."""
        try:
            # Attempt to parse standard OmniParser output format
            elements: list[dict[str, Any]] = []
            if hasattr(outputs, "boxes") and hasattr(outputs, "labels"):
                boxes = outputs.boxes.cpu().numpy()
                labels = outputs.labels
                scores = (
                    outputs.scores.cpu().numpy()
                    if hasattr(outputs, "scores")
                    else [1.0] * len(boxes)
                )
                img_w, img_h = image_size

                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box[:4]
                    elements.append({
                        "index": i,
                        "label": str(labels[i]) if labels else f"element_{i}",
                        "bbox": [
                            int(x1 * img_w),
                            int(y1 * img_h),
                            int(x2 * img_w),
                            int(y2 * img_h),
                        ],
                        "confidence": float(scores[i]) if scores else 1.0,
                        "type": "ui_element",
                    })

            return elements
        except Exception as e:
            logger.warning("Failed to parse OmniParser outputs: %s", e)
            return []

    def _annotate_image(self, image: Any, elements: list[dict[str, Any]]) -> str:
        """Draw bounding boxes on the image and return base64."""
        try:
            from PIL import ImageDraw, ImageFont

            annotated = image.copy()
            draw = ImageDraw.Draw(annotated)

            colors = ["#FF0000", "#00FF00", "#0000FF", "#FFA500", "#800080"]
            for i, elem in enumerate(elements):
                color = colors[i % len(colors)]
                bbox = elem.get("bbox", [])
                if len(bbox) == 4:
                    draw.rectangle(bbox, outline=color, width=2)
                    label = elem.get("label", f"#{i}")
                    draw.text(
                        (bbox[0], bbox[1] - 12),
                        f"{label} ({elem.get('confidence', 0):.2f})",
                        fill=color,
                    )

            buf = io.BytesIO()
            annotated.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

        except Exception as e:
            logger.warning("Failed to annotate image: %s", e)
            return ""

    def _get_device_context(self):
        """Return the appropriate device context manager."""
        try:
            import torch
            return torch.cuda.amp.autocast() if self._device == "cuda" else _NoOpContext()
        except ImportError:
            return _NoOpContext()

    def _get_no_grad(self):
        """Return no_grad context."""
        try:
            import torch
            return torch.no_grad()
        except ImportError:
            return _NoOpContext()


class _NoOpContext:
    """No-op context manager for when torch is not available."""
    def __enter__(self) -> None:
        pass
    def __exit__(self, *args: Any) -> None:
        pass


class SimpleGrounding(GroundingModel):
    """Lightweight grounding using accessibility tree + OCR only.

    Does not require a GPU or large model download. Uses the ACI
    (accessibility tree) for element detection and optional OCR for
    text elements not in the accessibility tree.
    """

    def __init__(self) -> None:
        super().__init__(model_name="simple", device="cpu")

    def load(self) -> None:
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def ground(
        self,
        image_base64: str,
        instruction: str = "",
    ) -> GroundingResult:
        """Use ACI tree for grounding (no ML model needed)."""
        import time

        start = time.time()

        try:
            from skpl_agent.desktop_automation import WindowsACI

            aci = WindowsACI(top_app_only=True, ocr=True)
            obs = {"screenshot": base64.b64decode(image_base64)}
            tree_text = aci.linearize_and_annotate_tree(obs)

            elements: list[dict[str, Any]] = []
            for i, node in enumerate(aci.nodes):
                pos = node.get("position", (0, 0))
                size = node.get("size", (0, 0))
                elements.append({
                    "index": i,
                    "label": node.get("text", "") or node.get("title", ""),
                    "bbox": [
                        pos[0], pos[1],
                        pos[0] + size[0], pos[1] + size[1],
                    ],
                    "confidence": 1.0,
                    "type": node.get("role", "unknown"),
                    "title": node.get("title", ""),
                })

            latency = (time.time() - start) * 1000

            return GroundingResult(
                elements=elements,
                instruction=instruction,
                model_used="simple_aci",
                latency_ms=round(latency, 2),
            )

        except Exception as e:
            logger.error("Simple grounding failed: %s", e)
            latency = (time.time() - start) * 1000
            return GroundingResult(
                elements=[],
                instruction=instruction,
                model_used="simple_aci",
                latency_ms=round(latency, 2),
            )


# ── Factory ──────────────────────────────────────────────────────────────

def create_grounding_model(
    model_type: str = "simple",
    model_name: str = "",
    device: str = "cpu",
) -> GroundingModel:
    """Factory function to create the appropriate grounding model.

    Args:
        model_type: "omniparser", "simple", or "none".
        model_name: Model name (for OmniParser).
        device: Device for inference (cpu/cuda/mps).

    Returns:
        GroundingModel instance.
    """
    if model_type == "omniparser":
        return OmniParserGrounding(
            model_name=model_name or "microsoft/OmniParser-v2",
            device=device,
        )
    elif model_type == "simple":
        return SimpleGrounding()
    else:
        return GroundingModel(model_name="none", device="cpu")