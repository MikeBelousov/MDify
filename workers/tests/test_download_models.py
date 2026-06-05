from __future__ import annotations

import hashlib

from workers.build import download_models


def test_existing_bad_model_is_re_downloaded(tmp_path, monkeypatch):
    expected_content = b"real model content"
    model_path = tmp_path / "det" / "model.onnx"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"git-lfs pointer or partial download")

    def fake_download(url: str, destination):
        assert url == "https://example.test/model.onnx"
        destination.write_bytes(expected_content)

    monkeypatch.setattr(download_models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(download_models, "download", fake_download)

    result = download_models.ensure_file(
        {
            "path": "det/model.onnx",
            "sha256": hashlib.sha256(expected_content).hexdigest(),
            "url": "https://example.test/model.onnx",
        },
        download_missing=True,
    )

    assert result is True
    assert model_path.read_bytes() == expected_content


def test_verify_only_bad_model_fails_without_download(tmp_path, monkeypatch):
    model_path = tmp_path / "rec" / "model.onnx"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"wrong content")

    def fail_download(url: str, destination):
        raise AssertionError("verify-only must not download")

    monkeypatch.setattr(download_models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(download_models, "download", fail_download)

    result = download_models.ensure_file(
        {
            "path": "rec/model.onnx",
            "sha256": hashlib.sha256(b"expected content").hexdigest(),
            "url": "https://example.test/model.onnx",
        },
        download_missing=False,
    )

    assert result is False
