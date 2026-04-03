"""
Unit tests for error handling and exception scenarios
"""

import os
import tempfile
from unittest.mock import MagicMock, patch, call
import pytest
import numpy as np
from scipy.io.wavfile import write as write_wav

from main import FnwisprClient


class TestModelLoadingErrors:
    """Test error handling during model loading"""

    def test_model_loading_failure_raises_exception(self, temp_config_file):
        """Test that failure to load model raises exception"""
        with patch("main.WhisperModel", side_effect=Exception("Model download failed")):
            with pytest.raises(Exception, match="Model download failed"):
                FnwisprClient(temp_config_file)

    def test_model_loading_logs_error(self, temp_config_file, caplog):
        """Test that model loading errors are logged"""
        with patch("main.WhisperModel", side_effect=Exception("Model error")):
            with pytest.raises(Exception):
                FnwisprClient(temp_config_file)
            assert "Failed to load Whisper model" in caplog.text


class TestConfigSaveErrors:
    """Test error handling when saving configuration"""

    def test_config_save_failure_logs_error(self, caplog):
        """Test that config save failures are logged"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            with patch("main.WhisperModel"):
                client = FnwisprClient.__new__(FnwisprClient)
                client.config = {}

                # Mock open to raise exception on write
                with patch("builtins.open", side_effect=Exception("Permission denied")):
                    config = client.create_default_config(temp_path)

                # Should still return default config even if save failed
                assert config is not None
                assert "hotkey" in config

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestAudioRecordingErrors:
    """Test error handling during audio recording"""

    def test_start_recording_stream_failure(self, temp_config_file, caplog):
        """Test handling of audio stream startup failure"""
        with patch("main.WhisperModel"):
            with patch("sounddevice.InputStream", side_effect=Exception("Device not found")):
                client = FnwisprClient(temp_config_file)

                # Should handle error gracefully
                client.start_recording()

                assert not client.recording
                assert "Failed to start audio recording" in caplog.text

    def test_stop_recording_stream_close_failure(self, temp_config_file, caplog):
        """Test handling of audio stream close failure"""
        with patch("main.WhisperModel"):
            with patch("sounddevice.InputStream"):
                client = FnwisprClient(temp_config_file)
                client.recording = True
                client.stream = MagicMock()
                client.stream.stop.side_effect = Exception("Stream close failed")

                with patch.object(client, "process_audio"):
                    client.stop_recording()

                assert not client.recording
                assert "Error stopping stream" in caplog.text

    def test_stop_recording_closes_stream(self, temp_config_file):
        """Test that stop_recording properly closes the stream"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.recording = True
            client.stream = MagicMock()

            with patch.object(client, "process_audio"):
                client.stop_recording()

            client.stream.stop.assert_called_once()
            client.stream.close.assert_called_once()


class TestAudioProcessingErrors:
    """Test error handling during audio processing"""

    def test_process_audio_wav_write_failure(self, temp_config_file):
        """Test handling of WAV file write failure"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            audio = np.sin(np.linspace(0, 1, 1000)).astype(np.float32)
            client.audio_data = [audio]

            with patch("scipy.io.wavfile.write", side_effect=Exception("Write failed")):
                # Should not raise, just handle gracefully
                client.process_audio()

    def test_process_audio_missing_wav_file(self, temp_config_file, caplog):
        """Test handling when WAV file is not created"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            audio = np.sin(np.linspace(0, 1, 1000)).astype(np.float32)
            client.audio_data = [audio]

            with patch("os.path.exists", return_value=False):
                with patch("scipy.io.wavfile.write"):
                    client.process_audio()

            assert "WAV file was not created" in caplog.text or "Error processing audio" in caplog.text

    def test_process_audio_temp_file_cleanup_failure(self, temp_config_file, caplog):
        """Test handling of temp file deletion failure"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            audio = np.sin(np.linspace(0, 1, 1000)).astype(np.float32)
            client.audio_data = [audio]

            def mock_exists(path):
                return True

            with patch("os.path.exists", side_effect=mock_exists):
                with patch("scipy.io.wavfile.write"):
                    with patch.object(client, "transcribe_audio", return_value="test"):
                        with patch.object(client, "insert_text"):
                            with patch("os.unlink", side_effect=Exception("Permission denied")):
                                client.process_audio()

            assert "Failed to delete temporary file" in caplog.text


class TestKeyboardHandlerErrors:
    """Test error handling in keyboard event handlers"""

    def test_on_press_exception_handling(self, temp_config_file):
        """Test that on_press handles exceptions gracefully"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            # Mock normalize_key to raise exception
            with patch.object(client, "normalize_key", side_effect=Exception("Key error")):
                # Should not raise, just handle gracefully
                result = client.on_press(None)
                # Should not return False (which would stop listener)
                assert result is None

    def test_on_release_exception_handling(self, temp_config_file):
        """Test that on_release handles exceptions gracefully"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            # Mock normalize_key to raise exception
            with patch.object(client, "normalize_key", side_effect=Exception("Key error")):
                # Should not raise, just handle gracefully
                result = client.on_release(None)
                # Should not return False (which would stop listener)
                assert result is None

    def test_on_press_starts_recording_when_hotkey_matched(self, temp_config_file):
        """Test that on_press starts recording when hotkey combo is pressed"""
        with patch("main.WhisperModel"):
            with patch("sounddevice.InputStream"):
                client = FnwisprClient(temp_config_file)
                client.hotkey_combo = {1, 2}  # Simple set of keys for testing

                with patch.object(client, "start_recording") as mock_start:
                    client.current_keys = {1}
                    normalized_key = 2
                    with patch.object(client, "normalize_key", return_value=normalized_key):
                        client.on_press(None)

                    mock_start.assert_called_once()

    def test_on_release_stops_recording_for_hotkey(self, temp_config_file):
        """Test that on_release stops recording when hotkey is released"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.recording = True
            client.hotkey_combo = {1, 2}

            with patch.object(client, "stop_recording") as mock_stop:
                normalized_key = 1  # One of the hotkey keys
                with patch.object(client, "normalize_key", return_value=normalized_key):
                    client.on_release(None)

                mock_stop.assert_called_once()

    def test_on_release_exits_on_escape(self, temp_config_file):
        """Test that on_release exits on Escape key"""
        with patch("main.WhisperModel"):
            from pynput import keyboard

            client = FnwisprClient(temp_config_file)
            assert client.is_running

            result = client.on_release(keyboard.Key.esc)

            assert not client.is_running
            assert result is False  # Returning False stops the listener


class TestNormalizeKey:
    """Test key normalization for left/right variants"""

    def test_normalize_ctrl_l_when_ctrl_in_combo(self, temp_config_file):
        """Test that ctrl_l normalizes to ctrl when ctrl is in hotkey"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.ctrl, keyboard.Key.cmd}

            result = client.normalize_key(keyboard.Key.ctrl_l)
            assert result == keyboard.Key.ctrl

    def test_normalize_ctrl_r_when_ctrl_in_combo(self, temp_config_file):
        """Test that ctrl_r normalizes to ctrl when ctrl is in hotkey"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.ctrl, keyboard.Key.cmd}

            result = client.normalize_key(keyboard.Key.ctrl_r)
            assert result == keyboard.Key.ctrl

    def test_normalize_alt_l_when_alt_in_combo(self, temp_config_file):
        """Test that alt_l normalizes to alt when alt is in hotkey"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.alt, keyboard.Key.shift}

            result = client.normalize_key(keyboard.Key.alt_l)
            assert result == keyboard.Key.alt

    def test_normalize_alt_r_when_alt_in_combo(self, temp_config_file):
        """Test that alt_r normalizes to alt when alt is in hotkey"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.alt, keyboard.Key.shift}

            result = client.normalize_key(keyboard.Key.alt_r)
            assert result == keyboard.Key.alt

    def test_normalize_shift_l_when_shift_in_combo(self, temp_config_file):
        """Test that shift_l normalizes to shift when shift is in hotkey"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.shift, keyboard.KeyCode.from_char('a')}

            result = client.normalize_key(keyboard.Key.shift_l)
            assert result == keyboard.Key.shift

    def test_normalize_shift_r_when_shift_in_combo(self, temp_config_file):
        """Test that shift_r normalizes to shift when shift is in hotkey"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.shift, keyboard.KeyCode.from_char('a')}

            result = client.normalize_key(keyboard.Key.shift_r)
            assert result == keyboard.Key.shift

    def test_no_normalize_when_base_not_in_combo(self, temp_config_file):
        """Test that left/right variants are NOT normalized when base key not in combo"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            # Hotkey specifies ctrl_l, not generic ctrl
            client.hotkey_combo = {keyboard.Key.ctrl_l, keyboard.Key.cmd}

            # ctrl_r should NOT normalize when only ctrl_l is in combo
            result = client.normalize_key(keyboard.Key.ctrl_r)
            assert result == keyboard.Key.ctrl_r

    def test_non_modifier_key_unchanged(self, temp_config_file):
        """Test that non-modifier keys are returned unchanged"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            from pynput import keyboard

            client.hotkey_combo = {keyboard.Key.ctrl}

            # 'a' key should be unchanged
            key_a = keyboard.KeyCode.from_char('a')
            result = client.normalize_key(key_a)
            assert result == key_a
