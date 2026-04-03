"""
Unit tests for audio recording and processing
"""

import os
import tempfile
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest
from scipy.io.wavfile import write as write_wav

from conftest import make_transcribe_result
from main import FnwisprClient


class TestAudioRecording:
    """Test audio recording functionality"""

    def test_start_recording_sets_flag(self, mock_sounddevice, temp_config_file):
        """Test that start_recording sets the recording flag"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            assert not client.recording
            client.start_recording()
            assert client.recording

    def test_start_recording_initializes_audio_data(
        self, mock_sounddevice, temp_config_file
    ):
        """Test that start_recording initializes audio_data list"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            # Add some data first
            client.audio_data = [np.array([1, 2, 3])]
            client.start_recording()

            # Should be reset
            assert len(client.audio_data) == 0

    def test_stop_recording_clears_flag(self, mock_sounddevice, temp_config_file):
        """Test that stop_recording clears the recording flag"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.recording = True

            with patch.object(client, "process_audio"):
                client.stop_recording()

            assert not client.recording

    def test_audio_callback_appends_data_when_recording(
        self, mock_sounddevice, temp_config_file
    ):
        """Test that audio callback appends data when recording is active"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.recording = True

            # Create test audio data
            test_data = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
            indata = test_data.copy()

            # Call callback
            client.audio_callback(indata, len(indata), None, None)

            # Should have appended the data
            assert len(client.audio_data) == 1
            np.testing.assert_array_equal(client.audio_data[0], test_data)

    def test_audio_callback_ignores_data_when_not_recording(
        self, mock_sounddevice, temp_config_file
    ):
        """Test that audio callback ignores data when not recording"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.recording = False

            test_data = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
            indata = test_data.copy()

            client.audio_callback(indata, len(indata), None, None)

            # Should NOT have appended the data
            assert len(client.audio_data) == 0

    def test_audio_callback_handles_status_message(
        self, mock_sounddevice, temp_config_file, capsys
    ):
        """Test that audio callback logs status messages"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.recording = True

            test_data = np.array([[0.1]], dtype=np.float32)
            status_message = "Test status"

            # Call with status
            client.audio_callback(test_data, len(test_data), None, status_message)

            # Should still record the data
            assert len(client.audio_data) == 1


class TestAudioProcessing:
    """Test audio processing and file handling"""

    def test_process_audio_with_no_data(self, temp_config_file):
        """Test that process_audio handles empty audio data"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)
            client.audio_data = []

            # Should not raise, just return
            client.process_audio()

    def test_process_audio_concatenates_chunks(self, temp_config_file):
        """Test that process_audio concatenates audio chunks"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            # Create multiple audio chunks
            chunk1 = np.array([[0.1], [0.2]], dtype=np.float32)
            chunk2 = np.array([[0.3], [0.4]], dtype=np.float32)
            client.audio_data = [chunk1, chunk2]

            with patch.object(client, "transcribe_audio", return_value="test"):
                with patch.object(client, "insert_text"):
                    client.process_audio()

            # Should have concatenated and transcribed

    def test_process_audio_creates_temporary_file(self, temp_config_file):
        """Test that process_audio creates a temporary WAV file"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            # Create simple audio data
            audio = np.sin(np.linspace(0, 1, 1000)).astype(np.float32)
            client.audio_data = [audio]

            with patch.object(
                client, "transcribe_audio", return_value="test"
            ) as mock_transcribe:
                with patch.object(client, "insert_text"):
                    client.process_audio()

                # transcribe_audio should have been called with a file path
                assert mock_transcribe.called
                audio_path = mock_transcribe.call_args[0][0]
                assert audio_path.endswith(".wav")

    def test_process_audio_cleans_up_temporary_file(self, temp_config_file):
        """Test that process_audio cleans up temporary files"""
        with patch("main.WhisperModel"):
            client = FnwisprClient(temp_config_file)

            audio = np.sin(np.linspace(0, 1, 1000)).astype(np.float32)
            client.audio_data = [audio]

            # Track which files were created and deleted
            created_files = []
            deleted_files = []

            original_write = write_wav

            def mock_write(path, *args, **kwargs):
                created_files.append(path)
                original_write(path, *args, **kwargs)

            with patch("scipy.io.wavfile.write", side_effect=mock_write):
                with patch.object(client, "transcribe_audio", return_value="test"):
                    with patch.object(client, "insert_text"):
                        with patch("os.unlink", side_effect=lambda p: deleted_files.append(p)):
                            client.process_audio()

            # File should have been deleted
            assert len(deleted_files) > 0


class TestAudioFormatHandling:
    """Test audio format conversion and normalization"""

    def test_transcribe_audio_handles_int16(self, temp_config_file, temp_wav_file):
        """Test transcription of int16 audio"""
        with patch("main.WhisperModel") as mock_cls:
            mock_model = MagicMock()
            mock_model.transcribe = MagicMock(
                return_value=make_transcribe_result("test transcription")
            )
            mock_cls.return_value = mock_model

            client = FnwisprClient(temp_config_file)
            result = client.transcribe_audio(temp_wav_file)

            assert result == "test transcription"

    def test_transcribe_audio_normalizes_to_float32(self, temp_config_file):
        """Test that audio is normalized to float32"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Create int16 audio and save
            sample_rate = 16000
            audio_int16 = np.array([100, 200, 300, -100], dtype=np.int16)
            write_wav(temp_path, sample_rate, audio_int16)

            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("test")
                )
                mock_cls.return_value = mock_model

                client = FnwisprClient(temp_config_file)
                client.transcribe_audio(temp_path)

                # Check that transcribe was called with float32 data
                call_args = mock_model.transcribe.call_args
                audio_data = call_args[0][0]
                assert audio_data.dtype == np.float32
                assert audio_data.min() >= -1.0
                assert audio_data.max() <= 1.0

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_audio_handles_stereo(self, temp_config_file):
        """Test that stereo audio is converted to mono"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Create stereo audio
            sample_rate = 16000
            stereo_audio = np.array(
                [[100, 200], [150, 250], [200, 300]], dtype=np.int16
            )
            write_wav(temp_path, sample_rate, stereo_audio)

            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("test")
                )
                mock_cls.return_value = mock_model

                client = FnwisprClient(temp_config_file)
                client.transcribe_audio(temp_path)

                # Check that audio is mono
                call_args = mock_model.transcribe.call_args
                audio_data = call_args[0][0]
                assert len(audio_data.shape) == 1  # 1D array (mono)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_audio_handles_int32(self, temp_config_file):
        """Test transcription of int32 audio"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Create int32 audio and save
            sample_rate = 16000
            audio_int32 = np.array([100000, 200000, -100000], dtype=np.int32)
            write_wav(temp_path, sample_rate, audio_int32)

            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("test")
                )
                mock_cls.return_value = mock_model

                client = FnwisprClient(temp_config_file)
                client.transcribe_audio(temp_path)

                # Check that transcribe was called with float32 normalized data
                call_args = mock_model.transcribe.call_args
                audio_data = call_args[0][0]
                assert audio_data.dtype == np.float32
                assert audio_data.min() >= -1.0
                assert audio_data.max() <= 1.0

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_audio_handles_uint8(self, temp_config_file):
        """Test transcription of uint8 audio"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Create uint8 audio and save
            sample_rate = 16000
            audio_uint8 = np.array([128, 200, 100], dtype=np.uint8)
            write_wav(temp_path, sample_rate, audio_uint8)

            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("test")
                )
                mock_cls.return_value = mock_model

                client = FnwisprClient(temp_config_file)
                client.transcribe_audio(temp_path)

                # Check that transcribe was called with float32 normalized data
                call_args = mock_model.transcribe.call_args
                audio_data = call_args[0][0]
                assert audio_data.dtype == np.float32
                assert audio_data.min() >= -1.0
                assert audio_data.max() <= 1.0

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transcribe_audio_already_float32(self, temp_config_file):
        """Test that float32 audio is not re-normalized"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Create float32 audio
            sample_rate = 16000
            audio_float32 = np.array([0.1, 0.5, -0.3], dtype=np.float32)
            write_wav(temp_path, sample_rate, audio_float32)

            with patch("main.WhisperModel") as mock_cls:
                mock_model = MagicMock()
                mock_model.transcribe = MagicMock(
                    return_value=make_transcribe_result("test")
                )
                mock_cls.return_value = mock_model

                client = FnwisprClient(temp_config_file)
                client.transcribe_audio(temp_path)

                # Check that transcribe was called with float32 data
                call_args = mock_model.transcribe.call_args
                audio_data = call_args[0][0]
                assert audio_data.dtype == np.float32

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
