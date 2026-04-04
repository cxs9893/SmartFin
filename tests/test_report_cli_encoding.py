from __future__ import annotations

from io import BytesIO

from finqa import cli


class ReconfigurableTextStream:
    def __init__(self, encoding: str = "gbk") -> None:
        self.encoding = encoding
        self.text = ""

    def reconfigure(self, encoding: str | None = None, **_: object) -> None:
        if encoding:
            self.encoding = encoding

    def write(self, data: str) -> int:
        data.encode(self.encoding)
        self.text += data
        return len(data)

    def flush(self) -> None:
        return None


class BufferFallbackStream:
    def __init__(self) -> None:
        self.buffer = BytesIO()

    def write(self, data: str) -> int:
        raise UnicodeEncodeError("gbk", data, 0, 1, "codec can't encode character")

    def flush(self) -> None:
        return None


def test_emit_json_reconfigure_to_utf8(monkeypatch):
    stream = ReconfigurableTextStream()
    monkeypatch.setattr(cli.sys, "stdout", stream)

    payload = {"report_zh": "跨年报告 ☒"}
    cli._emit_json(payload)

    assert stream.encoding.lower() == "utf-8"
    assert "跨年报告" in stream.text


def test_emit_json_fallback_to_stdout_buffer(monkeypatch):
    stream = BufferFallbackStream()
    monkeypatch.setattr(cli.sys, "stdout", stream)

    payload = {"report_zh": "单年报告 ☒"}
    cli._emit_json(payload)

    output = stream.buffer.getvalue().decode("utf-8")
    assert "单年报告" in output
