"""Developer unit cases only; do not read the independently held-out test set."""
import json
from pathlib import Path

import pytest

from sign_robot import language, llm
from sign_robot.contracts import load_catalog, validate_selection


@pytest.fixture
def catalog():
    return load_catalog()


@pytest.mark.parametrize("text,expected", [
    ("HELLO!", "HELLO"), ("  Hi there. ", "HELLO"),
    ("Thank YOU very much!", "THANK_YOU"),
    ("please    wait", "PLEASE_WAIT"), ("hold on a moment", "PLEASE_WAIT"),
])
def test_exact_normalized_full_expression(text, expected, catalog):
    answer = language.select_action(text, catalog=catalog)
    assert answer["status"] == "execute"
    assert answer["action_id"] == expected
    assert answer["method"] == "exact"
    assert answer["latency_ms"] >= 0
    validate_selection(answer, catalog)


@pytest.mark.parametrize("text", [
    "My password contains hello", "The word thankful contains thank",
    "Thanks but please move", "Do not wait", "I don't want to wait",
    "No thanks", "Please wait outside", "Wait for the physician",
    "I will wait", "Thank her", 'She said "hello"',
    "Hello. Please take your medicine.", "Please wait\nbring a chair",
    "Please wait five minutes", "请稍等", "Say hello", "Thanks for nothing",
])
@pytest.mark.parametrize("method", ["exact", "embedding", "llm"])
def test_shared_boundaries_do_not_execute(text, method, catalog, monkeypatch):
    # Unknown remainder must not become exact substring matching, and shared
    # boundary guards precede either model. Disable model availability here.
    monkeypatch.setattr(language, "_embedding", lambda *_: ("error", None, "embedding_unavailable"))
    monkeypatch.setattr(llm, "choose_local", lambda *_, **__: ("error", None, "llm_unavailable"))
    answer = language.select_action(text, method, catalog)
    assert answer["status"] != "execute"
    assert answer["action_id"] is None
    validate_selection(answer, catalog)


@pytest.mark.parametrize("text", ["hello and thank you", "thanks, please wait", "hello then bring water"])
def test_mixed_intents_request_clarification(text, catalog):
    answer = language.select_action(text, catalog=catalog)
    assert answer["status"] == "clarify"
    assert answer["action_id"] is None


def test_empty_invalid_and_unknown_inputs(catalog):
    assert language.select_action(" ", catalog=catalog)["status"] == "clarify"
    assert language.select_action(None, catalog=catalog)["reason_code"] == "invalid_input_type"
    assert language.select_action("hello", "bogus", catalog)["status"] == "error"
    assert language.select_action("hello", catalog=[])["status"] == "error"


def test_embedding_missing_weights_is_not_an_exact_fallback(tmp_path, catalog, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/embedding.json").write_text(json.dumps({"model_path": "missing"}))
    monkeypatch.setattr(language, "ROOT", tmp_path)
    result = language.select_action("hello", "embedding", catalog)
    assert result["status"] == "error"
    assert result["reason_code"] == "embedding_unavailable"
    assert result["method"] == "embedding"


def test_llm_unconfigured_is_not_an_exact_fallback(tmp_path, catalog, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/llm.json").write_text('{"endpoint": null, "model": null}')
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    result = language.select_action("hello", "llm", catalog)
    assert result["status"] == "error"
    assert result["reason_code"] == "llm_unavailable"
    assert result["action_id"] is None
    assert result["metadata"]["request_attempted"] is False


def test_explicit_llm_config_override_inside_project(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    custom = tmp_path / "config/research.json"
    custom.write_text('{"endpoint":null,"model":null}')
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    monkeypatch.setenv("SIGN_ROBOT_LLM_CONFIG", "config/research.json")
    assert llm._config_path() == custom


@pytest.mark.parametrize("relative", ["../outside.json", "data/catalog.json", "config/../outside.json", "config/model.py"])
def test_llm_config_override_rejects_escape_and_nonjson(tmp_path, monkeypatch, relative):
    (tmp_path / "config").mkdir()
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    monkeypatch.setenv("SIGN_ROBOT_LLM_CONFIG", relative)
    with pytest.raises(ValueError):
        llm._config_path()


def test_llm_config_override_rejects_symlink_escape(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    (tmp_path / "config/link.json").symlink_to(outside)
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    monkeypatch.setenv("SIGN_ROBOT_LLM_CONFIG", "config/link.json")
    with pytest.raises(ValueError):
        llm._config_path()


def test_shared_guard_does_not_claim_an_llm_call(catalog):
    result = language.select_action("Do not wait", "llm", catalog)
    assert result["status"] == "unsupported"
    assert "metadata" not in result


@pytest.mark.parametrize("payload", [
    {"status": "execute", "action_id": "DROP_TABLE"},
    {"status": "execute", "action_id": None},
    {"status": "execute", "action_id": 1},
    {"status": "unsupported", "action_id": "HELLO"},
    {"status": "execute", "action_id": "HELLO", "joint_commands": [999]},
    {"status": ["execute"], "action_id": "HELLO"},
    "HELLO", None,
])
def test_invalid_llm_output_fails_closed(payload, catalog):
    status, action_id, _ = llm.validate_llm_choice(payload, catalog)
    assert status == "error"
    assert action_id is None


def test_llm_valid_output(catalog):
    assert llm.validate_llm_choice({"status": "execute", "action_id": "HELLO"}, catalog)[:2] == ("execute", "HELLO")
    assert llm.validate_llm_choice({"status": "clarify", "action_id": None}, catalog)[:2] == ("clarify", None)


@pytest.mark.parametrize("content", [
    "execute", "The answer is HELLO", "HELLO because this is a greeting", '"HELLO"',
    "HELLO.", "HELLO\nTHANK_YOU", "hello", '{"action_id":"HELLO"}', None,
])
def test_label_parser_never_extracts_or_guesses(content, catalog):
    assert llm.validate_llm_label(content, catalog) == ("error", None, "llm_invalid_label")


@pytest.mark.parametrize("content,expected", [
    ("HELLO", ("execute", "HELLO")),
    (" THANK_YOU\n", ("execute", "THANK_YOU")),
    ("PLEASE_WAIT", ("execute", "PLEASE_WAIT")),
    ("UNSUPPORTED", ("unsupported", None)),
    ("CLARIFY", ("clarify", None)),
])
def test_label_parser_accepts_complete_whitelisted_labels(content, expected, catalog):
    assert llm.validate_llm_label(content, catalog)[:2] == expected


@pytest.mark.parametrize("endpoint", [
    "https://api.example.com/v1/chat/completions",
    "http://localhost.evil.test/v1/chat/completions",
    "http://127.0.0.1@evil.test/v1/chat/completions",
    "http://127.0.0.1:8000/another-path", "http://127.0.0.1/v1/chat/completions?token=secret", 123,
])
def test_remote_or_credential_endpoints_are_rejected(endpoint):
    assert not llm._loopback_endpoint(endpoint)


def test_explicit_loopback_allowed():
    assert llm._loopback_endpoint("http://127.0.0.1:8000/v1/chat/completions")
    assert llm._loopback_endpoint("http://[::1]:8000/v1/chat/completions")


@pytest.mark.parametrize("mode,content", [
    ("json", '{"status":"execute","action_id":"PLEASE_WAIT"}'),
    ("label", "PLEASE_WAIT"),
])
def test_llm_http_response_validated(tmp_path, catalog, monkeypatch, mode, content):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/llm.json").write_text(json.dumps({
        "endpoint": "http://127.0.0.1:8000/v1/chat/completions", "model": "local-test", "output_mode": mode}))
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    seen = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return json.dumps({"choices": [{"message": {"content": content}}]}).encode()

    class Opener:
        def open(self, request, timeout):
            seen.append(json.loads(request.data))
            assert request.get_header("Authorization") is None
            return Response()

    monkeypatch.setattr(llm, "build_opener", lambda *_: Opener())
    result = language.select_action("please wait", "llm", catalog)
    assert result["action_id"] == "PLEASE_WAIT"
    assert seen[0]["messages"][-1]["content"] == "please wait"
    assert seen[0]["temperature"] == 0
    assert ("response_format" in seen[0]) is (mode == "json")
    assert result["metadata"]["request_attempted"] is True
    assert result["metadata"]["response_received"] is True
    assert result["metadata"]["raw_model_output"] == content
    assert len(result["metadata"]["response_sha256"]) == 64
