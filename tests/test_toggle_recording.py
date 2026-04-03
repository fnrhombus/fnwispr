"""
Tests for toggle (double-tap) recording mode
"""

import json
import tempfile
import time
import os
from unittest.mock import patch, MagicMock

import pytest
from pynput import keyboard

from main import FnwisprClient


def _make_client(config_overrides=None):
    """Create a FnwisprClient with mocked Whisper and a toggle-mode config."""
    config = {
        "hotkey": "ctrl+alt",
        "recording_mode": "toggle",
        "toggle_key": "ctrl_l",
        "double_tap_interval": 0.3,
        "model": "base",
        "sample_rate": 16000,
        "microphone_device": None,
        "language": None,
    }
    if config_overrides:
        config.update(config_overrides)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f)
        temp_path = f.name

    with patch("whisper.load_model"):
        client = FnwisprClient(temp_path)

    # Clean up temp config
    os.unlink(temp_path)
    return client


class TestParseSingleKey:
    """Test _parse_single_key method"""

    def test_parse_ctrl_l(self):
        client = _make_client()
        assert client._parse_single_key("ctrl_l") == keyboard.Key.ctrl_l

    def test_parse_ctrl_r(self):
        client = _make_client()
        assert client._parse_single_key("ctrl_r") == keyboard.Key.ctrl_r

    def test_parse_generic_ctrl(self):
        client = _make_client()
        assert client._parse_single_key("ctrl") == keyboard.Key.ctrl

    def test_parse_alt_variants(self):
        client = _make_client()
        assert client._parse_single_key("alt") == keyboard.Key.alt
        assert client._parse_single_key("alt_l") == keyboard.Key.alt_l
        assert client._parse_single_key("alt_r") == keyboard.Key.alt_r

    def test_parse_shift_variants(self):
        client = _make_client()
        assert client._parse_single_key("shift") == keyboard.Key.shift
        assert client._parse_single_key("shift_l") == keyboard.Key.shift_l
        assert client._parse_single_key("shift_r") == keyboard.Key.shift_r

    def test_parse_win(self):
        client = _make_client()
        assert client._parse_single_key("win") == keyboard.Key.cmd

    def test_parse_single_char(self):
        client = _make_client()
        result = client._parse_single_key("a")
        assert result == keyboard.KeyCode.from_char("a")

    def test_parse_unknown_defaults_to_ctrl_l(self):
        client = _make_client()
        assert client._parse_single_key("nonexistent") == keyboard.Key.ctrl_l

    def test_case_insensitive(self):
        client = _make_client()
        assert client._parse_single_key("CTRL_L") == keyboard.Key.ctrl_l
        assert client._parse_single_key("Alt_R") == keyboard.Key.alt_r


class TestIsToggleKey:
    """Test _is_toggle_key method"""

    def test_exact_match(self):
        client = _make_client({"toggle_key": "ctrl_l"})
        assert client._is_toggle_key(keyboard.Key.ctrl_l) is True
        assert client._is_toggle_key(keyboard.Key.ctrl_r) is False

    def test_generic_ctrl_matches_both(self):
        client = _make_client({"toggle_key": "ctrl"})
        assert client._is_toggle_key(keyboard.Key.ctrl_l) is True
        assert client._is_toggle_key(keyboard.Key.ctrl_r) is True
        assert client._is_toggle_key(keyboard.Key.ctrl) is True

    def test_generic_alt_matches_both(self):
        client = _make_client({"toggle_key": "alt"})
        assert client._is_toggle_key(keyboard.Key.alt_l) is True
        assert client._is_toggle_key(keyboard.Key.alt_r) is True

    def test_generic_shift_matches_both(self):
        client = _make_client({"toggle_key": "shift"})
        assert client._is_toggle_key(keyboard.Key.shift_l) is True
        assert client._is_toggle_key(keyboard.Key.shift_r) is True

    def test_no_match(self):
        client = _make_client({"toggle_key": "ctrl_l"})
        assert client._is_toggle_key(keyboard.Key.alt_l) is False
        assert client._is_toggle_key(keyboard.Key.shift_l) is False


class TestToggleRecordingMode:
    """Test the double-tap toggle recording state machine"""

    def test_first_tap_does_not_start_recording(self):
        """First tap should only record the timestamp, not start recording."""
        client = _make_client()
        client.start_recording = MagicMock()

        client.on_press(keyboard.Key.ctrl_l)

        client.start_recording.assert_not_called()
        assert client._last_toggle_tap_time > 0

    def test_double_tap_starts_recording(self):
        """Two taps within the interval should start recording."""
        client = _make_client()
        client.start_recording = MagicMock()

        # First tap
        client.on_press(keyboard.Key.ctrl_l)
        client.on_release(keyboard.Key.ctrl_l)

        # Second tap (within interval)
        client.on_press(keyboard.Key.ctrl_l)

        client.start_recording.assert_called_once()

    def test_slow_double_tap_does_not_start(self):
        """Two taps outside the interval should not start recording."""
        client = _make_client({"double_tap_interval": 0.1})
        client.start_recording = MagicMock()

        # First tap
        client.on_press(keyboard.Key.ctrl_l)
        client.on_release(keyboard.Key.ctrl_l)

        # Wait longer than interval
        time.sleep(0.15)

        # Second tap (outside interval)
        client.on_press(keyboard.Key.ctrl_l)

        client.start_recording.assert_not_called()

    def test_third_tap_stops_recording(self):
        """Third tap while recording should stop recording."""
        client = _make_client()
        client.start_recording = MagicMock()
        client.stop_recording = MagicMock()

        # Simulate already recording
        client.recording = True

        client.on_press(keyboard.Key.ctrl_l)

        client.stop_recording.assert_called_once()

    def test_release_does_not_stop_recording(self):
        """In toggle mode, releasing the key should NOT stop recording."""
        client = _make_client()
        client.stop_recording = MagicMock()
        client.recording = True

        client.on_release(keyboard.Key.ctrl_l)

        client.stop_recording.assert_not_called()

    def test_key_repeat_ignored(self):
        """Holding the key down (repeat events) should not count as multiple taps."""
        client = _make_client()
        client.start_recording = MagicMock()

        # First press
        client.on_press(keyboard.Key.ctrl_l)
        # Simulated key repeats (no release in between)
        client.on_press(keyboard.Key.ctrl_l)
        client.on_press(keyboard.Key.ctrl_l)

        # Should not have started recording (repeats don't count)
        client.start_recording.assert_not_called()

    def test_held_flag_clears_on_release(self):
        """Release should clear the held flag so next press is a new tap."""
        client = _make_client()

        client.on_press(keyboard.Key.ctrl_l)
        assert client._toggle_key_held is True

        client.on_release(keyboard.Key.ctrl_l)
        assert client._toggle_key_held is False

    def test_escape_still_exits_in_toggle_mode(self):
        """ESC should still shut down the app in toggle mode."""
        client = _make_client()

        result = client.on_release(keyboard.Key.esc)

        assert client.is_running is False
        assert result is False

    def test_non_toggle_key_ignored(self):
        """Pressing a non-toggle key should not affect toggle state."""
        client = _make_client({"toggle_key": "ctrl_l"})
        client.start_recording = MagicMock()

        client.on_press(keyboard.Key.alt_l)
        client.on_release(keyboard.Key.alt_l)
        client.on_press(keyboard.Key.alt_l)

        client.start_recording.assert_not_called()
        assert client._last_toggle_tap_time == 0.0


class TestHoldModeUnchanged:
    """Verify hold mode still works correctly when recording_mode is 'hold'"""

    def test_hold_starts_on_combo(self):
        """Hold mode should start recording when hotkey combo is held."""
        client = _make_client({"recording_mode": "hold"})
        client.start_recording = MagicMock()

        client.on_press(keyboard.Key.ctrl)
        client.on_press(keyboard.Key.alt)

        client.start_recording.assert_called()

    def test_hold_stops_on_release(self):
        """Hold mode should stop recording when hotkey key is released."""
        client = _make_client({"recording_mode": "hold"})
        client.stop_recording = MagicMock()
        client.recording = True
        # Put keys in current_keys so discard works
        client.current_keys = {keyboard.Key.ctrl, keyboard.Key.alt}

        client.on_release(keyboard.Key.ctrl)

        client.stop_recording.assert_called_once()


class TestConfigBackfill:
    """Test that existing configs get new fields backfilled"""

    def test_missing_fields_backfilled(self):
        """Loading an old config without toggle fields should add defaults."""
        old_config = {
            "hotkey": "ctrl+alt",
            "model": "base",
            "sample_rate": 16000,
            "microphone_device": None,
            "language": None,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(old_config, f)
            temp_path = f.name

        try:
            with patch("whisper.load_model"):
                client = FnwisprClient(temp_path)

            assert "recording_mode" in client.config
            assert "toggle_key" in client.config
            assert "double_tap_interval" in client.config

            # Verify file was updated
            with open(temp_path) as f:
                saved = json.load(f)
            assert "recording_mode" in saved
            assert "toggle_key" in saved
            assert "double_tap_interval" in saved
        finally:
            os.unlink(temp_path)

    def test_existing_fields_not_overwritten(self):
        """Backfill should not overwrite fields that already exist."""
        config = {
            "hotkey": "ctrl+alt",
            "recording_mode": "hold",
            "toggle_key": "alt_l",
            "double_tap_interval": 0.5,
            "model": "base",
            "sample_rate": 16000,
            "microphone_device": None,
            "language": None,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch("whisper.load_model"):
                client = FnwisprClient(temp_path)

            assert client.config["recording_mode"] == "hold"
            assert client.config["toggle_key"] == "alt_l"
            assert client.config["double_tap_interval"] == 0.5
        finally:
            os.unlink(temp_path)
