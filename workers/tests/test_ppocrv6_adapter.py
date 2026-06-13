from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from workers.ocr.ppocrv6_adapter import PPOCRV6OutputError, PPOCRV6Recognizer


class FakeInput:
    name = "images"
    shape = [None, 3, 48, None]


class FakeSession:
    def __init__(self, output: np.ndarray) -> None:
        self.output = output
        self.feeds: list[dict[str, np.ndarray]] = []

    def get_inputs(self) -> list[FakeInput]:
        return [FakeInput()]

    def run(self, _outputs, feed: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.feeds.append(feed)
        return [self.output]


def write_dictionary(tmp_path: Path) -> Path:
    dictionary_path = tmp_path / "dict.txt"
    dictionary_path.write_text("A\nB\n", encoding="utf-8")
    return dictionary_path


def logits_for(*class_sequences: list[int]) -> np.ndarray:
    logits = np.full((len(class_sequences), 4, 3), -10.0, dtype=np.float32)
    for batch_index, sequence in enumerate(class_sequences):
        for timestep, class_index in enumerate(sequence):
            logits[batch_index, timestep, class_index] = 10.0
    return logits


def test_preserve_input_order(tmp_path: Path) -> None:
    session = FakeSession(logits_for([1, 2, 0, 0], [2, 1, 0, 0]))
    recognizer = PPOCRV6Recognizer.from_session(session, write_dictionary(tmp_path))
    images = [
        Image.new("RGB", (80, 24), "white"),
        Image.new("RGB", (120, 24), "white"),
    ]

    results = recognizer.recognize(images)

    assert [text for text, _confidence in results] == ["AB", "BA"]
    assert len(session.feeds) == 1
    assert session.feeds[0]["images"].shape[0] == len(images)


def test_rejects_mismatched_output_count(tmp_path: Path) -> None:
    session = FakeSession(logits_for([1, 2, 0, 0]))
    recognizer = PPOCRV6Recognizer.from_session(session, write_dictionary(tmp_path))
    images = [
        Image.new("RGB", (80, 24), "white"),
        Image.new("RGB", (120, 24), "white"),
    ]

    with pytest.raises(PPOCRV6OutputError, match="expected 2 recognition outputs, got 1"):
        recognizer.recognize(images)


def test_rejects_non_finite_confidence(tmp_path: Path) -> None:
    logits = logits_for([1, 2, 0, 0])
    logits[0, 0, :] = np.nan
    session = FakeSession(logits)
    recognizer = PPOCRV6Recognizer.from_session(session, write_dictionary(tmp_path))

    with pytest.raises(PPOCRV6OutputError, match="confidence"):
        recognizer.recognize([Image.new("RGB", (80, 24), "white")])


def test_prepares_images_in_bgr_channel_order(tmp_path: Path) -> None:
    session = FakeSession(logits_for([1, 0, 0, 0]))
    recognizer = PPOCRV6Recognizer.from_session(session, write_dictionary(tmp_path))

    recognizer.recognize([Image.new("RGB", (1, 1), (255, 0, 0))])

    first_pixel = session.feeds[0]["images"][0, :, 0, 0]
    assert first_pixel.tolist() == [-1.0, -1.0, 1.0]


def test_preserves_probability_confidence(tmp_path: Path) -> None:
    probabilities = np.array(
        [[[0.05, 0.90, 0.05], [0.90, 0.05, 0.05]]],
        dtype=np.float32,
    )
    session = FakeSession(probabilities)
    recognizer = PPOCRV6Recognizer.from_session(session, write_dictionary(tmp_path))

    result = recognizer.recognize([Image.new("RGB", (80, 24), "white")])

    assert result[0][0] == "A"
    assert result[0][1] == pytest.approx(0.9)


def test_pads_batch_with_normalized_zero(tmp_path: Path) -> None:
    session = FakeSession(logits_for([1, 0, 0, 0], [2, 0, 0, 0]))
    recognizer = PPOCRV6Recognizer.from_session(session, write_dictionary(tmp_path))

    recognizer.recognize(
        [
            Image.new("RGB", (1, 1), "white"),
            Image.new("RGB", (2, 1), "white"),
        ]
    )

    short_image_padding = session.feeds[0]["images"][0, :, :, -1]
    assert np.all(short_image_padding == 0.0)
