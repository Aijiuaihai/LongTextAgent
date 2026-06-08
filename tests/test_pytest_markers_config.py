from pathlib import Path


def test_pytest_markers_configured() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'addopts = ["-m", "not integration"]' in pyproject
    assert "integration: tests requiring local services" in pyproject
    assert "ollama: tests requiring Ollama" in pyproject
    assert "chroma: tests requiring Chroma persistence" in pyproject
    assert "slow: slow tests" in pyproject
