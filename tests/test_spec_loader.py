import logging
from pathlib import Path

import pytest

from app.agents.spec_loader import AgentSpecConfig, SpecAgent, load_spec_directory


def test_from_dict_well_formed() -> None:
    data = {
        "name": "assistant",
        "description": "Helpful assistant",
        "instructions": "You are helpful.",
        "capabilities": ["search", "calendar"],
        "model": "main",
        "streaming": True,
        "voice_reply": True,
    }
    spec = AgentSpecConfig.from_dict(data)
    assert spec.name == "assistant"
    assert spec.description == "Helpful assistant"
    assert spec.instructions == "You are helpful."
    assert spec.capabilities == ["search", "calendar"]
    assert spec.model == "main"
    assert spec.streaming is True
    assert spec.voice_reply is True


def test_from_dict_missing_required_field() -> None:
    data = {
        "name": "assistant",
        "description": "Helpful assistant",
        "instructions": "You are helpful.",
    }
    with pytest.raises(ValueError, match="Missing required fields: capabilities"):
        AgentSpecConfig.from_dict(data)


def test_from_dict_extra_keys_ignored() -> None:
    data = {
        "name": "assistant",
        "description": "Helpful assistant",
        "instructions": "You are helpful.",
        "capabilities": [],
        "unknown_key": "should be ignored",
    }
    spec = AgentSpecConfig.from_dict(data)
    assert spec.name == "assistant"
    assert not hasattr(spec, "unknown_key")


def test_load_spec_directory_loads_single_yaml(tmp_path: Path) -> None:
    spec_path = tmp_path / "assistant.yaml"
    spec_path.write_text(
        "name: assistant\n"
        "description: Helpful assistant\n"
        "instructions: You are helpful.\n"
        "capabilities:\n  - search\n"
    )
    specs = load_spec_directory(tmp_path)
    assert len(specs) == 1
    assert specs[0].name == "assistant"


def test_load_spec_directory_skips_underscore_files(tmp_path: Path) -> None:
    draft_path = tmp_path / "_draft.yaml"
    draft_path.write_text(
        "name: draft\n"
        "description: Draft\n"
        "instructions: Draft instructions.\n"
        "capabilities: []\n"
    )
    specs = load_spec_directory(tmp_path)
    assert specs == []


def test_load_spec_directory_bad_yaml_logs_and_skips(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("not: valid: [yaml")
    good_path = tmp_path / "good.yaml"
    good_path.write_text(
        "name: good\n"
        "description: Good\n"
        "instructions: Good instructions.\n"
        "capabilities: []\n"
    )
    with caplog.at_level(logging.ERROR):
        specs = load_spec_directory(tmp_path)
    assert len(specs) == 1
    assert specs[0].name == "good"


def test_load_spec_directory_empty(tmp_path: Path) -> None:
    specs = load_spec_directory(tmp_path)
    assert specs == []


async def test_spec_agent_run_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = AgentSpecConfig.from_dict(
        {
            "name": "assistant",
            "description": "Helpful assistant",
            "instructions": "You are helpful.",
            "capabilities": [],
        }
    )

    class FakeResult:
        data = "hello"

    class FakeAgent:
        async def run(self, message: str, **kwargs: object) -> FakeResult:
            return FakeResult()

    monkeypatch.setattr(
        "app.agents.spec_loader.SpecAgent.get_agent",
        lambda self: FakeAgent(),
    )

    agent = SpecAgent(spec)
    result = await agent.run("hi")
    assert isinstance(result, str)
    assert result == "hello"
