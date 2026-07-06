import pytest

from app.services import deepseek_client as deepseek_module
from app.services.deepseek_client import DeepSeekClient


class _FakeResponse:
    status_code = 200

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "ok"}'
                    }
                }
            ]
        }


class _FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.calls.append(kwargs["json"])
        return _FakeResponse()


@pytest.mark.asyncio
async def test_deepseek_client_uses_allowed_model_by_analysis_type(monkeypatch):
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(deepseek_module.httpx, "AsyncClient", _FakeAsyncClient)

    client = DeepSeekClient()

    await client.analyze_tender_documents("title", "description", "documents", analysis_type="quick")
    await client.analyze_tender_documents("title", "description", "documents", analysis_type="deep")

    assert _FakeAsyncClient.calls[0]["model"] == "deepseek-v4-flash"
    assert _FakeAsyncClient.calls[1]["model"] == "deepseek-v4-pro"
    deprecated_model = "deepseek" + "-chat"
    assert all(call["model"] != deprecated_model for call in _FakeAsyncClient.calls)
