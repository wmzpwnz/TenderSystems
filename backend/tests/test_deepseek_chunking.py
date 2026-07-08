import pytest

from app.services.deepseek_client import DeepSeekClient


def test_split_documents_text_prefers_document_markers():
    client = DeepSeekClient()
    documents_text = (
        "Вводная часть тендера\n\n"
        "=== first.pdf ===\n"
        "Первый документ\n\n"
        "=== second.pdf ===\n"
        "Второй документ"
    )

    blocks = client._split_documents_text(documents_text)

    assert blocks[0] == "Вводная часть тендера"
    assert blocks[1].startswith("=== first.pdf ===")
    assert blocks[2].startswith("=== second.pdf ===")


def test_split_documents_text_falls_back_to_sections_without_markers():
    client = DeepSeekClient()
    documents_text = "Раздел 1\nстрока\n\nРаздел 2\nстрока\n\nРаздел 3\nстрока"

    blocks = client._split_documents_text(documents_text)

    assert blocks == [
        "Раздел 1\nстрока",
        "Раздел 2\nстрока",
        "Раздел 3\nстрока",
    ]


@pytest.mark.asyncio
async def test_prepare_documents_text_skips_chunking_when_text_fits(monkeypatch):
    client = DeepSeekClient()
    called = False

    async def fail_summarize(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("summary call should not happen when text fits")

    monkeypatch.setattr(client, "_summarize_chunk_text", fail_summarize)

    result = await client._prepare_documents_text("короткий текст", 100, "quick")

    assert result == "короткий текст"
    assert called is False


@pytest.mark.asyncio
async def test_prepare_documents_text_summarizes_chunked_documents(monkeypatch):
    client = DeepSeekClient()
    calls = []
    documents_text = (
        "=== first.pdf ===\n" + ("A" * 70) + "\n\n"
        "=== second.pdf ===\n" + ("B" * 70) + "\n\n"
        "=== third.pdf ===\n" + ("C" * 70)
    )

    async def fake_summarize(**kwargs):
        calls.append(kwargs)
        return f"summary-{kwargs['chunk_index']}"

    monkeypatch.setattr(client, "_summarize_chunk_text", fake_summarize)

    result = await client._prepare_documents_text(documents_text, 150, "quick")

    assert len([call for call in calls if call["stage"] == "document"]) >= 2
    assert "анализ выполнен по чанкам документов" in result
    assert "summary-1" in result


@pytest.mark.asyncio
async def test_prepare_documents_text_recompresses_large_summaries(monkeypatch):
    client = DeepSeekClient()
    calls = []
    documents_text = (
        "=== first.pdf ===\n" + ("A" * 70) + "\n\n"
        "=== second.pdf ===\n" + ("B" * 70)
    )

    async def fake_summarize(**kwargs):
        calls.append(kwargs)
        if kwargs["stage"] == "document":
            return "X" * 45
        return f"compressed-{kwargs['chunk_index']}"

    monkeypatch.setattr(client, "_summarize_chunk_text", fake_summarize)

    result = await client._prepare_documents_text(documents_text, 150, "quick")

    assert any(call["stage"] == "compression" for call in calls)
    assert "compressed-" in result


@pytest.mark.asyncio
async def test_prepare_documents_text_falls_back_to_truncation_with_warning(monkeypatch, caplog):
    client = DeepSeekClient()
    documents_text = "Z" * 200

    def fail_split(_documents_text):
        raise RuntimeError("chunking unavailable")

    monkeypatch.setattr(client, "_split_documents_text", fail_split)

    with caplog.at_level("WARNING"):
        result = await client._prepare_documents_text(documents_text, 100, "quick")

    assert "DeepSeek quick analysis documents text truncated from 200 to 100 characters" in caplog.text
    assert "текст документов обрезан до 100 символов из 200" in result
