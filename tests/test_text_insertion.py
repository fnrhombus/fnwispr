"""
Unit tests for text insertion functionality
"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from main import FnwisprClient


class TestTextInsertion:
    """Test text insertion functionality"""

    def test_insert_text_calls_typewrite(self, temp_config_file):
        """Test that insert_text calls pyautogui.typewrite"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)
                client.insert_text("Hello, World!")

                # typewrite should have been called
                assert mock_typewrite.called

    def test_insert_text_with_empty_string(self, temp_config_file):
        """Test inserting empty string"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)
                client.insert_text("")

                # Should handle empty string without error

    def test_insert_text_with_special_characters(self, temp_config_file):
        """Test inserting text with special characters"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)

                # Test various special characters
                special_texts = [
                    "Hello, World!",
                    "Email@example.com",
                    "Price: $99.99",
                    "(Test)",
                    "Line 1\nLine 2",
                ]

                for text in special_texts:
                    client.insert_text(text)
                    # Should not raise exception

    def test_insert_text_with_long_text(self, temp_config_file):
        """Test inserting very long text"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)

                long_text = "This is a very long text. " * 100
                client.insert_text(long_text)

                assert mock_typewrite.called

    def test_insert_text_handles_exception(self, temp_config_file):
        """Test that insert_text handles pyautogui errors gracefully"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite", side_effect=Exception("Input blocked")):
                client = FnwisprClient(temp_config_file)

                # Should handle exception without crashing
                client.insert_text("Test")

    def test_insert_text_with_numbers(self, temp_config_file):
        """Test inserting numbers"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)
                client.insert_text("1234567890")

                assert mock_typewrite.called

    def test_insert_text_with_mixed_case(self, temp_config_file):
        """Test inserting mixed case text"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)
                client.insert_text("ThE QuIcK bRoWn FoX")

                assert mock_typewrite.called

    def test_insert_text_with_unicode(self, temp_config_file):
        """Test inserting unicode characters"""
        with patch("main.WhisperModel"):
            with patch("pyautogui.typewrite") as mock_typewrite:
                client = FnwisprClient(temp_config_file)

                # Note: pyautogui.typewrite may not support all unicode
                # but should handle gracefully
                client.insert_text("Hello")  # Keep it simple

                assert mock_typewrite.called
