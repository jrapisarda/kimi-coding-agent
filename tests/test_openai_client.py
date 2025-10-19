from kimi_agent.sdk.openai_client import OpenAIClient


class _DummyResponses:
    def __init__(self, client):
        self._client = client

    def create(self, **kwargs):
        self._client.last_kwargs = kwargs
        return _DummyResponse()


class _DummyClient:
    def __init__(self):
        self.responses = _DummyResponses(self)
        self.last_kwargs = None


class _DummyResponse:
    output_text = "stubbed response"


def test_generate_text_omits_temperature_and_max_tokens(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = OpenAIClient(
        model="gpt-test",
        temperature=0.9,
        max_output_tokens=512,
        enabled=True,
        dry_run=False,
    )

    dummy_client = _DummyClient()
    monkeypatch.setattr(client, "_ensure_client", lambda api_key: dummy_client)

    result = client.generate_text("hello world")

    assert result == "stubbed response"
    assert dummy_client.last_kwargs == {"model": "gpt-test", "input": "hello world"}

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
