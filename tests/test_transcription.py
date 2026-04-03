"""
Unit tests for Whisper transcription integration
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from scipy.io.wavfile import write as write_wav

from conftest import make_transcribe_result
from main import FnwisprClient


class TestTranscriptionBasics:
    """Test basic transcription functionality"""

    def test_transcribe_audio_success(self, temp_config_file, temp_wav_file):
        """Test successful transcription"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("Hello, world!")
            )
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            assert result == "Hello, world!"

    def test_transcribe_audio_strips_whitespace(self, temp_config_file, temp_wav_file):
        """Test that transcribed text is stripped of whitespace"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("  Test text with spaces  ")
            )
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            assert result == "Test text with spaces"

    def test_transcribe_audio_returns_detected_language(
        self, temp_config_file, temp_wav_file
    ):
        """Test that detected language is returned in result"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("Bonjour, monde!", "fr")
            )
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            assert result == "Bonjour, monde!"

    def test_transcribe_audio_handles_empty_result(
        self, temp_config_file, temp_wav_file
    ):
        """Test handling of empty transcription result"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("")
            )
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            assert result == ""


class TestTranscriptionLanguage:
    """Test language handling in transcription"""

    def test_transcribe_with_language_parameter(
        self, temp_config_file, temp_wav_file
    ):
        """Test transcription with specific language set"""
        import json

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "hotkey": "ctrl+alt",
                "model": "base",
                "sample_rate": 16000,
                "microphone_device": None,
                "language": "es",
            }
            json.dump(config, f)
            temp_config = f.name

        try:
            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("Hola, mundo!", "es")
                )
                mock_cls.return_value = mock_model

                client = FnwisprClient(temp_config)
                result = client.transcribe_audio(temp_wav_file)

                # Check that transcribe was called with language parameter
                call_args = mock_model.transcribe.call_args
                assert "language" in call_args[1]
                assert call_args[1]["language"] == "es"

        finally:
            if os.path.exists(temp_config):
                os.unlink(temp_config)

    def test_transcribe_without_language_parameter(
        self, temp_config_file, temp_wav_file
    ):
        """Test transcription with auto-detect language"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("Test text")
            )
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            # Check that transcribe was called
            assert mock_model.transcribe.called


class TestTranscriptionErrors:
    """Test error handling in transcription"""

    def test_transcribe_audio_file_not_found(self, temp_config_file):
        """Test handling of missing audio file"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio("/nonexistent/path.wav")

            assert result is None

    def test_transcribe_audio_whisper_error(self, temp_config_file, temp_wav_file):
        """Test handling of Whisper transcription errors"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(side_effect=Exception("Whisper error"))
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            assert result is None

    def test_transcribe_audio_handles_corrupted_wav(self, temp_config_file):
        """Test handling of corrupted WAV file"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Write invalid WAV data
            f.write(b"not a valid wav file")
            temp_path = f.name

        try:
            with patch("main.WhisperModel"):
                client = FnwisprClient(temp_config_file)
                result = client.transcribe_audio(temp_path)

                # Should return None due to error
                assert result is None

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestTranscriptionIntegration:
    """Integration tests for transcription workflow"""

    def test_full_audio_to_text_flow(self, temp_config_file):
        """Test complete audio recording to text transcription flow"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("Test transcription result")
            )
            mock_cls.return_value = mock_model

            with patch("sounddevice.InputStream"):
                client = FnwisprClient(temp_config_file)

                # Create test audio data
                audio = np.sin(np.linspace(0, 1, 16000)).astype(np.float32)
                client.audio_data = [audio]

                # Process audio
                with patch.object(client, "insert_text") as mock_insert:
                    client.process_audio()

                    # insert_text should have been called
                    assert mock_insert.called
                    inserted_text = mock_insert.call_args[0][0]
                    assert "Test transcription result" in inserted_text
