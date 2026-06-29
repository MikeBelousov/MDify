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


def test_missing_git_lfs_model_does_not_download_source_url(tmp_path, monkeypatch, capsys):
    def fail_download(url: str, destination):
        raise AssertionError(f"Git LFS entry must not download source_url: {url}")

    monkeypatch.setattr(download_models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(download_models, "download", fail_download)

    result = download_models.ensure_file(
        {
            "path": "rec/PP-OCRv6_medium_rec.onnx",
            "distribution": "git-lfs",
            "source_url": "https://example.test/PP-OCRv6_medium_rec_infer.tar",
            "sha256": hashlib.sha256(b"expected model").hexdigest(),
        },
        download_missing=True,
    )

    captured = capsys.readouterr()
    assert result is False
    assert (
        "missing Git LFS OCR model: rec/PP-OCRv6_medium_rec.onnx; run git lfs pull"
        in captured.err
    )


def test_verify_model_file_set_rejects_unlisted_model(
    tmp_path,
    monkeypatch,
    capsys,
):
    listed = tmp_path / "rec/eslav.onnx"
    listed.parent.mkdir(parents=True)
    listed.write_bytes(b"listed")
    (tmp_path / "rec/PP-OCRv6_medium_rec.onnx").write_bytes(b"stale")
    monkeypatch.setattr(download_models, "MODELS_DIR", tmp_path)

    result = download_models.verify_model_file_set(
        [{"path": "rec/eslav.onnx"}]
    )

    assert result is False
    assert "unlisted OCR model" in capsys.readouterr().err


def test_verify_model_file_set_accepts_exact_manifest(tmp_path, monkeypatch):
    listed = tmp_path / "rec/eslav.onnx"
    listed.parent.mkdir(parents=True)
    listed.write_bytes(b"listed")
    monkeypatch.setattr(download_models, "MODELS_DIR", tmp_path)

    assert download_models.verify_model_file_set(
        [{"path": "rec/eslav.onnx"}]
    )
