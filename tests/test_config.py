"""
Unit tests for configuration loading and management
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import after sys.path modification in conftest
from main import FnwisprClient


class TestConfigLoading:
    """Test configuration file loading"""

    def test_load_config_from_file(self, temp_config_file):
        """Test loading config from an existing file"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            assert client.config["hotkey"] == "ctrl+alt"
            assert client.config["model"] == "base"
            assert client.config["sample_rate"] == 16000

    def test_load_config_creates_default_if_missing(self):
        """Test that default config is created if file doesn't exist"""
        with patch("main.WhisperModel"):
            nonexistent_path = "/tmp/nonexistent_config_12345.json"
            client = FnwisprClient(nonexistent_path)

            # Should have default config
            assert client.config["hotkey"] == "ctrl+win"
            assert client.config["model"] == "base"
            assert client.config["sample_rate"] == 16000
            assert client.config["microphone_device"] is None
            assert client.config["language"] is None

    def test_load_config_invalid_json(self):
        """Test handling of invalid JSON in config file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            with patch("main.WhisperModel"):
                with pytest.raises(SystemExit):
                    FnwisprClient(temp_path)
        finally:
            os.unlink(temp_path)

    def test_config_default_values(self, temp_config_file):
        """Test that config has all required default values"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            assert "hotkey" in client.config
            assert "model" in client.config
            assert "sample_rate" in client.config
            assert "microphone_device" in client.config
            assert "language" in client.config

    def test_config_custom_values(self):
        """Test loading config with custom values"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+shift+s",
                "model": "small",
                "sample_rate": 16000,
                "microphone_device": 2,
                "language": "es",
            }
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch("main.WhisperModel"):
                client = FnwisprClient(temp_path)
                assert client.config["hotkey"] == "ctrl+shift+s"
                assert client.config["model"] == "small"
                assert client.config["microphone_device"] == 2
                assert client.config["language"] == "es"
        finally:
            os.unlink(temp_path)


class TestHotkeyParsing:
    """Test hotkey string parsing"""

    def test_parse_simple_modifier(self):
        """Test parsing simple modifier combinations"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            hotkey = client.parse_hotkey("ctrl+alt")
            assert len(hotkey) == 2

    def test_parse_ctrl_variants(self):
        """Test parsing ctrl with specific variants"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            # Generic ctrl should work
            hotkey_generic = client.parse_hotkey("ctrl+win")
            assert len(hotkey_generic) == 2

            # Specific variants should work
            hotkey_l = client.parse_hotkey("ctrl_l+win")
            assert len(hotkey_l) == 2

            hotkey_r = client.parse_hotkey("ctrl_r+win")
            assert len(hotkey_r) == 2

    def test_parse_alt_variants(self):
        """Test parsing alt with specific variants"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            hotkey_generic = client.parse_hotkey("alt+shift")
            assert len(hotkey_generic) == 2

            hotkey_l = client.parse_hotkey("alt_l+shift")
            assert len(hotkey_l) == 2

            hotkey_r = client.parse_hotkey("alt_r+shift")
            assert len(hotkey_r) == 2

    def test_parse_shift_variants(self):
        """Test parsing shift with specific variants"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            hotkey_generic = client.parse_hotkey("shift+s")
            assert len(hotkey_generic) == 2

            hotkey_l = client.parse_hotkey("shift_l+s")
            assert len(hotkey_l) == 2

            hotkey_r = client.parse_hotkey("shift_r+s")
            assert len(hotkey_r) == 2

    def test_parse_hotkey_with_character(self):
        """Test parsing hotkey with regular character"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            hotkey = client.parse_hotkey("ctrl+shift+a")
            assert len(hotkey) == 3

    def test_parse_hotkey_whitespace_handling(self):
        """Test that whitespace is handled correctly"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            # With spaces
            hotkey_spaces = client.parse_hotkey("ctrl + alt + shift")
            # Without spaces
            hotkey_no_spaces = client.parse_hotkey("ctrl+alt+shift")

            # Both should parse to same result
            assert len(hotkey_spaces) == len(hotkey_no_spaces)

    def test_parse_hotkey_case_insensitive(self):
        """Test that hotkey parsing is case insensitive"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            hotkey_lower = client.parse_hotkey("ctrl+alt+a")
            hotkey_upper = client.parse_hotkey("CTRL+ALT+A")

            # Should parse to same result
            assert len(hotkey_lower) == len(hotkey_upper)

    def test_parse_invalid_key(self):
        """Test parsing with unknown keys"""
        with patch("main.WhisperModel"):
            client = FnwisprClient.__new__(FnwisprClient)
            client.config = {}

            # Should still work but might not include unknown key
            hotkey = client.parse_hotkey("ctrl+invalidkey")
            assert len(hotkey) >= 1  # At least ctrl should be parsed
