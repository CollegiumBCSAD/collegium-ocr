import pytest
from fastapi import HTTPException

from app import main as main_module


def test_require_api_key_allows_any_header_when_unset(monkeypatch):
    monkeypatch.setattr(main_module, "OCR_API_KEY", "")
    main_module.require_api_key(x_api_key="")


def test_require_api_key_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(main_module, "OCR_API_KEY", "secret")
    with pytest.raises(HTTPException) as exc_info:
        main_module.require_api_key(x_api_key="wrong")
    assert exc_info.value.status_code == 401


def test_require_api_key_accepts_correct_key(monkeypatch):
    monkeypatch.setattr(main_module, "OCR_API_KEY", "secret")
    main_module.require_api_key(x_api_key="secret")
