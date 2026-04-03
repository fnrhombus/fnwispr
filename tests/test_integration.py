"""
End-to-end integration tests for the complete fnwispr workflow
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest
from scipy.io.wavfile import write as write_wav

from conftest import make_transcribe_result
from main import FnwisprClient


class TestEndToEndWorkflow:
    """End-to-end integration tests"""

    def test_complete_hotkey_recording_transcription_flow(self):
        """Test complete workflow: hotkey → record → transcribe → insert text"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 16000,
                "microphone_device": None,
                "language": None,
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel") as mock_cls:
                # Setup mock Whisper
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("Hello world")
                )
                mock_cls.return_value = mock_model

                with patch("sounddevice.InputStream"):
                    with patch("pyautogui.typewrite") as mock_typewrite:
                        # Create client
                        client = FnwisprClient(temp_config)

                        # Simulate recording audio
                        audio_data = np.sin(
                            np.linspace(0, 1, 16000)
                        ).astype(np.float32)
                        client.audio_data = [audio_data]

                        # Process the audio
                        client.process_audio()

                        # Verify Whisper was called
                        assert mock_model.transcribe.called

                        # Verify text was inserted
                        # Note: typewrite may be called character by character
                        assert mock_typewrite.called

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)

    def test_multiple_consecutive_recordings(self):
        """Test multiple consecutive recording and transcription cycles"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 16000,
                "microphone_device": None,
                "language": None,
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()

                # Setup different responses for each call
                responses = [
                    make_transcribe_result("First recording"),
                    make_transcribe_result("Second recording"),
                    make_transcribe_result("Third recording"),
                ]
                mock_model.transcribe = MagicMock(side_effect=responses)
                mock_cls.return_value = mock_model

                with patch("sounddevice.InputStream"):
                    with patch("pyautogui.typewrite"):
                        client = FnwisprClient(temp_config)

                        # Simulate 3 recording cycles
                        for i, expected_text in enumerate(
                            ["First recording", "Second recording", "Third recording"]
                        ):
                            client.audio_data = [
                                np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
                            ]
                            client.process_audio()

                            # Verify Whisper was called correct number of times
                            assert mock_model.transcribe.call_count == i + 1

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)

    def test_workflow_with_different_languages(self):
        """Test workflow with different language configurations"""
        for language in [None, "en", "es", "fr"]:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                config = {
                    "hotkey": "ctrl+alt",
                    "model": "base",
                    "sample_rate": 16000,
                    "microphone_device": None,
                    "language": language,
                }
                json.dump(config, f)
                temp_config = f.name

            try:
                with patch("main.WhisperModel") as mock_cls:
                    mock_model = MagicMock()
                    mock_model.transcribe = MagicMock(
                        return_value=make_transcribe_result("Test", language or "en")
                    )
                    mock_cls.return_value = mock_model

                    with patch("sounddevice.InputStream"):
                        with patch("pyautogui.typewrite"):
                            client = FnwisprClient(temp_config)
                            assert client.config["language"] == language

            finally:
                if os.path.exists(temp_config):
                    os.unlink(temp_config)

    def test_workflow_with_different_models(self):
        """Test workflow with different Whisper model sizes"""
        for model_size in ["tiny", "base", "small"]:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                config = {
                    "hotkey": "ctrl+alt",
                    "model": model_size,
                    "sample_rate": 16000,
                    "microphone_device": None,
                    "language": None,
                }
                json.dump(config, f)
                temp_config = f.name

            try:
                with patch("main.WhisperModel") as mock_cls:
                    mock_model = MagicMock()
                    mock_cls.return_value = mock_model

                    with patch("sounddevice.InputStream"):
                        client = FnwisprClient(temp_config)
                        assert client.config["model"] == model_size

                        # Verify WhisperModel was called with correct model size as first arg
                        assert mock_cls.call_args[0][0] == model_size

            finally:
                if os.path.exists(temp_config):
                    os.unlink(temp_config)


class TestErrorRecovery:
    """Test error handling and recovery in end-to-end workflows"""

    def test_recovery_from_transcription_failure(self):
        """Test that system recovers if transcription fails"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 16000,
                "microphone_device": None,
                "language": None,
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()

                # First call fails, second succeeds
                mock_model.transcribe = MagicMock(
                    side_effect=[
                        Exception("Transcription failed"),
                        make_transcribe_result("Success"),
                    ]
                )
                mock_cls.return_value = mock_model

                with patch("sounddevice.InputStream"):
                    with patch("pyautogui.typewrite") as mock_typewrite:
                        client = FnwisprClient(temp_config)

                        # First attempt fails
                        client.audio_data = [
                            np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
                        ]
                        client.process_audio()
                        first_call_count = mock_typewrite.call_count

                        # Second attempt succeeds
                        client.audio_data = [
                            np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
                        ]
                        client.process_audio()

                        # Second call should have added to typewrite calls
                        # (or stayed same if first failed and insert_text wasn't called)
                        assert mock_model.transcribe.call_count == 2

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)

    def test_recovery_from_invalid_audio_data(self):
        """Test handling of invalid audio data"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 16000,
                "microphone_device": None,
                "language": None,
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("Normal transcription")
                )
                mock_cls.return_value = mock_model

                with patch("sounddevice.InputStream"):
                    with patch("pyautogui.typewrite"):
                        client = FnwisprClient(temp_config)

                        # Process empty audio
                        client.audio_data = []
                        client.process_audio()  # Should not crash

                        # Process valid audio after error
                        client.audio_data = [
                            np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
                        ]
                        client.process_audio()  # Should work

                        # Whisper should only be called once (for the valid audio)
                        assert mock_model.transcribe.call_count == 1

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)


class TestConfigurationVariations:
    """Test workflow with various configuration options"""

    def test_workflow_with_custom_microphone_device(self):
        """Test that custom microphone device is used"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 16000,
                "microphone_device": 2,
                "language": None,
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel"):
                with patch("sounddevice.InputStream") as mock_stream:
                    client = FnwisprClient(temp_config)
                    client.start_recording()

                    # Check that InputStream was called with correct device
                    call_kwargs = mock_stream.call_args[1]
                    assert call_kwargs["device"] == 2

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)

    def test_workflow_with_custom_sample_rate(self):
        """Test workflow with custom sample rate"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 44100,
                "microphone_device": None,
                "language": None,
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel"):
                with patch("sounddevice.InputStream") as mock_stream:
                    client = FnwisprClient(temp_config)
                    assert client.sample_rate == 44100

                    client.start_recording()

                    # Check that InputStream was called with correct sample rate
                    call_kwargs = mock_stream.call_args[1]
                    assert call_kwargs["samplerate"] == 44100

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)
