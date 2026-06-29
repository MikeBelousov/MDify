from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image


class PPOCRV6OutputError(RuntimeError):
    pass


class PPOCRV6Recognizer:
    MAX_DYNAMIC_WIDTH = 2048

    def __init__(self, model_path: Path | str, dictionary_path: Path | str) -> None:
        import onnxruntime

        self._session = onnxruntime.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self._characters = self._load_characters(dictionary_path)

    @classmethod
    def from_session(
        cls,
        session: Any,
        dictionary_path: Path | str,
    ) -> "PPOCRV6Recognizer":
        recognizer = cls.__new__(cls)
        recognizer._session = session
        recognizer._characters = cls._load_characters(dictionary_path)
        return recognizer

    @staticmethod
    def _load_characters(dictionary_path: Path | str) -> tuple[str, ...]:
        return tuple(Path(dictionary_path).read_text(encoding="utf-8").splitlines())

    def recognize(self, images: Sequence[Image.Image | np.ndarray]) -> list[tuple[str, float]]:
        if not images:
            return []

        input_metadata = self._session.get_inputs()
        if len(input_metadata) != 1:
            raise PPOCRV6OutputError(
                f"expected one ONNX input, got {len(input_metadata)}"
            )

        input_tensor = self._prepare_batch(images, input_metadata[0].shape)
        outputs = self._session.run(None, {input_metadata[0].name: input_tensor})
        if len(outputs) != 1:
            raise PPOCRV6OutputError(f"expected one ONNX output, got {len(outputs)}")

        logits = np.asarray(outputs[0])
        if logits.ndim != 3:
            raise PPOCRV6OutputError(
                f"expected rank-3 recognition output, got shape {logits.shape}"
            )
        if logits.shape[0] != len(images):
            raise PPOCRV6OutputError(
                f"expected {len(images)} recognition outputs, got {logits.shape[0]}"
            )
        expected_classes = len(self._characters) + 1
        if logits.shape[2] != expected_classes:
            raise PPOCRV6OutputError(
                f"expected {expected_classes} output classes, got {logits.shape[2]}"
            )

        probabilities = self._as_probabilities(logits)
        return [self._decode(sequence) for sequence in probabilities]

    @staticmethod
    def _as_bgr_image(image: Image.Image | np.ndarray) -> Image.Image:
        """Return channel values in BGR order.

        PIL inputs follow PIL's RGB contract. NumPy inputs follow RapidOCR's
        BGR crop contract.
        """
        if isinstance(image, Image.Image):
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
            return Image.fromarray(np.ascontiguousarray(rgb[:, :, ::-1]))

        bgr = np.asarray(image)
        if bgr.ndim != 3 or bgr.shape[2] != 3:
            raise ValueError(
                f"expected a BGR image with shape HxWx3, got {bgr.shape}"
            )
        return Image.fromarray(np.ascontiguousarray(bgr))

    @staticmethod
    def _prepare_batch(
        images: Sequence[Image.Image | np.ndarray],
        input_shape: Sequence[Any],
    ) -> np.ndarray:
        height = (
            input_shape[2]
            if len(input_shape) > 2 and isinstance(input_shape[2], int)
            else 48
        )
        fixed_width = (
            input_shape[3]
            if len(input_shape) > 3 and isinstance(input_shape[3], int)
            else None
        )

        converted: list[Image.Image] = []
        resized_widths: list[int] = []
        for image in images:
            bgr_image = PPOCRV6Recognizer._as_bgr_image(image)
            width = max(
                1,
                round(bgr_image.width * height / max(1, bgr_image.height)),
            )
            converted.append(bgr_image)
            width_limit = fixed_width or PPOCRV6Recognizer.MAX_DYNAMIC_WIDTH
            resized_widths.append(min(width, width_limit))

        batch_width = fixed_width or max(resized_widths)
        batch = np.zeros((len(images), 3, height, batch_width), dtype=np.float32)
        for index, (image, width) in enumerate(zip(converted, resized_widths, strict=True)):
            resized = image.resize((width, height), Image.Resampling.BILINEAR)
            array = np.asarray(resized, dtype=np.float32) / 127.5 - 1.0
            batch[index, :, :, :width] = array.transpose(2, 0, 1)
        return batch

    @staticmethod
    def _as_probabilities(logits: np.ndarray) -> np.ndarray:
        if not np.all(np.isfinite(logits)):
            raise PPOCRV6OutputError("recognition confidence is not finite")
        if (
            np.all(logits >= 0.0)
            and np.all(logits <= 1.0)
            and np.allclose(np.sum(logits, axis=2), 1.0, atol=1e-4)
        ):
            return logits

        shifted = logits - np.max(logits, axis=2, keepdims=True)
        exponentials = np.exp(shifted)
        probabilities = exponentials / np.sum(exponentials, axis=2, keepdims=True)
        if not np.all(np.isfinite(probabilities)):
            raise PPOCRV6OutputError("recognition confidence is not finite")
        return probabilities

    def _decode(self, probabilities: np.ndarray) -> tuple[str, float]:
        class_indices = np.argmax(probabilities, axis=1)
        class_confidences = np.max(probabilities, axis=1)
        text: list[str] = []
        selected_confidences: list[float] = []
        previous_index = 0
        for class_index, confidence in zip(
            class_indices,
            class_confidences,
            strict=True,
        ):
            current_index = int(class_index)
            if current_index != 0 and current_index != previous_index:
                text.append(self._characters[current_index - 1])
                selected_confidences.append(float(confidence))
            previous_index = current_index

        mean_confidence = (
            sum(selected_confidences) / len(selected_confidences)
            if selected_confidences
            else 0.0
        )
        if not math.isfinite(mean_confidence) or not 0.0 <= mean_confidence <= 1.0:
            raise PPOCRV6OutputError(
                f"recognition confidence out of range: {mean_confidence}"
            )
        return "".join(text), mean_confidence
