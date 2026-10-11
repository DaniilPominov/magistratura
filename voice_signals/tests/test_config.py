"""Tests for configuration loading and validation."""

from voice_signals.config import config_hash, load_config, validate_config


def test_load_config() -> None:
    """Test loading the default configuration."""
    config = load_config("configs/default.yaml")
    assert config["version"] == "0.1.0"
    assert "framing" in config
    assert "vad" in config
    assert "taxonomy" in config


def test_config_hash_determinism() -> None:
    """Test that config hash is deterministic."""
    config = load_config("configs/default.yaml")
    hash1 = config_hash(config)
    hash2 = config_hash(config)
    assert hash1 == hash2
    assert len(hash1) == 16


def test_config_hash_changes_with_content() -> None:
    """Test that config hash changes when content changes."""
    config1 = {"version": "0.1.0", "framing": {"sample_rate": 16000}}
    config2 = {"version": "0.1.0", "framing": {"sample_rate": 8000}}
    assert config_hash(config1) != config_hash(config2)


def test_validate_config_success() -> None:
    """Test that valid config passes validation."""
    config = load_config("configs/default.yaml")
    validate_config(config)  # Should not raise


def test_validate_config_missing_field() -> None:
    """Test that missing required field raises ValueError."""
    config = {"version": "0.1.0", "framing": {}}
    try:
        validate_config(config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "missing required config field" in str(e)
