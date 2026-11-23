import importlib.util
import json
from pathlib import Path

import pytest

script = Path(__file__).resolve().parents[2] / "decode_barcode.py"
spec = importlib.util.spec_from_file_location("decode_barcode", script)
assert spec and spec.loader
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)


def test_binderbyte_uses_anteraja_and_keeps_key_out_of_output(monkeypatch, capsys):
    monkeypatch.setenv("CEKRIR_BINDERBYTE_API_KEY", "test-key")
    calls = []

    def check(settings, payload):
        calls.append((settings, payload))
        return {"summary": {"status": "DELIVERED"}, "detail": {}, "history": []}

    monkeypatch.setattr(decoder, "check_tracking", check)
    result = decoder.lookup_anteraja("abc123")
    assert calls[0][1].courier == "anteraja"
    assert calls[0][1].resi_number == "ABC123"
    assert calls[0][0].binderbyte_api_key.get_secret_value() == "test-key"
    assert "test-key" not in json.dumps(result)
    assert "test-key" not in capsys.readouterr().out


def test_multiple_barcodes_do_not_trigger_lookup(monkeypatch, tmp_path, capsys):
    image = tmp_path / "test.jpg"
    image.write_bytes(b"image")
    monkeypatch.setattr(decoder.sys, "argv", ["decode_barcode.py", str(image)])
    monkeypatch.setattr(decoder, "decode_frame", lambda _: ["ONE123", "TWO456"])
    monkeypatch.setattr(
        decoder, "lookup_anteraja", lambda _: pytest.fail("Lookup must not be called")
    )
    assert decoder.main() == 1
    assert "More than one barcode" in capsys.readouterr().out


def test_decode_only_does_not_trigger_lookup(monkeypatch, tmp_path, capsys):
    image = tmp_path / "test.jpg"
    image.write_bytes(b"image")
    monkeypatch.setattr(decoder.sys, "argv", ["decode_barcode.py", str(image), "--decode-only"])
    monkeypatch.setattr(decoder, "decode_frame", lambda _: ["ONE123"])
    monkeypatch.setattr(
        decoder, "lookup_anteraja", lambda _: pytest.fail("Lookup must not be called")
    )
    assert decoder.main() == 0
    assert "ONE123" in capsys.readouterr().out
