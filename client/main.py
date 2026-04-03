"""
fnwispr - Windows Speech-to-Text Hotkey Application
Captures audio when hotkey is pressed and inserts transcribed text using local Whisper
"""

import importlib.resources
from pathlib import Path


def _read_version() -> str:
    """Read version from VERSION file, handling both dev and PyInstaller environments."""
    # Development: VERSION is at repo root (parent of client/)
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    # PyInstaller: VERSION is bundled alongside main.py
    version_file = Path(__file__).parent / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


__version__ = _read_version()

import json
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional
import traceback
import uuid
import winreg
import numpy as np
import pyautogui
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard
from scipy.io.wavfile import write as write_wav

# Import GUI components
from alerts import AlertManager
from tray import TrayManager
from gui import SettingsWindow

# Configure logging - use user profile directory
log_dir = Path.home() / ".fnwispr"
log_dir.mkdir(exist_ok=True)
log_path = log_dir / "fnwispr_client.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_path)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FnwisprClient:
    """
    Windows client for fnwispr speech-to-text service with system tray GUI
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the client

        Args:
            config_path: Path to configuration file (uses user profile if not specified)
        """
        self.config_path = self._get_config_path(config_path)
        self.config = self.load_config(self.config_path)
        self.recording = False
        self.audio_data = []
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.is_running = True
        self.current_keys = set()
        self.stream = None
        self.previous_device = self.config.get("microphone_device")

        # GUI components
        self.tray_manager = None
        self.settings_window = None
        self.alert_manager = AlertManager()

        # Keyboard listener thread
        self.listener_thread = None

        # Parse hotkey combination
        self.hotkey_combo = self.parse_hotkey(self.config.get("hotkey", "ctrl+win"))
        logger.info(f"Hotkey combination: {self.config.get('hotkey', 'ctrl+win')}")

        # Load Whisper model
        self._load_whisper_model()

        # Initialize microphone with error handling
        self._init_microphone(is_startup=True)

    def _get_config_path(self, provided_path: Optional[str] = None) -> str:
        """
        Get config path, with migration from old location if needed

        Args:
            provided_path: Explicitly provided config path

        Returns:
            Path to config file
        """
        if provided_path:
            return provided_path

        # Use user profile directory
        config_dir = Path.home() / ".fnwispr"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.json"

        # Migrate from old location if needed
        old_config = Path("config.json")
        if old_config.exists() and not config_path.exists():
            logger.info(f"Migrating config from {old_config} to {config_path}")
            try:
                with open(old_config, 'r') as f:
                    old_config_data = json.load(f)
                # Add new fields with defaults
                old_config_data.setdefault("auto_start", False)
                old_config_data.setdefault("close_behavior", "ask")
                with open(config_path, 'w') as f:
                    json.dump(old_config_data, f, indent=2)
                logger.info("Config migration completed")
            except Exception as e:
                logger.error(f"Failed to migrate config: {e}")

        return str(config_path)

    def _load_whisper_model(self):
        """Load Whisper model with error handling"""
        model_name = self.config.get("model", "base")
        logger.info(f"Loading Whisper model: {model_name}")
        try:
            # Use CUDA if available, otherwise CPU with int8 quantization for speed
            device = "cuda" if self._cuda_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            self.whisper_model = WhisperModel(model_name, device=device, compute_type=compute_type)
            logger.info(f"Whisper model '{model_name}' loaded successfully (device={device}, compute_type={compute_type})")
        except Exception as e:
            logger.error(f"Failed to load Whisper model '{model_name}': {e}")
            raise

    @staticmethod
    def _cuda_available() -> bool:
        """Check if CUDA is available for faster-whisper (CTranslate2)"""
        try:
            import ctranslate2
            return "cuda" in ctranslate2.get_supported_compute_types("cuda")
        except Exception:
            return False

    def _init_microphone(self, is_startup: bool = False):
        """
        Initialize microphone with error handling

        Args:
            is_startup: Whether this is initial startup
        """
        device_idx = self.config.get("microphone_device")
        device_name = self._get_device_name(device_idx)

        try:
            # Try to create a test stream
            test_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=device_idx
            )
            test_stream.close()
            logger.info(f"Microphone initialized successfully: {device_name}")
        except Exception as e:
            logger.error(f"Failed to initialize microphone '{device_name}': {e}")
            self.alert_manager.show_mic_error(device_name, str(e), is_startup=is_startup)

    def _get_device_name(self, device_idx: Optional[int]) -> str:
        """Get device name from index"""
        if device_idx is None:
            return "Default"
        try:
            devices = sd.query_devices()
            if 0 <= device_idx < len(devices):
                return devices[device_idx]["name"]
        except Exception:
            pass
        return f"Device {device_idx}"

    def load_config(self, config_path: str) -> dict:
        """
        Load configuration from JSON file

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            logger.info("Creating default configuration file...")
            default_config = self.create_default_config(config_path)
            return default_config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def create_default_config(self, config_path: str) -> dict:
        """
        Create default configuration file

        Args:
            config_path: Path where config should be saved

        Returns:
            Default configuration dictionary
        """
        default_config = {
            "hotkey": "ctrl+win",
            "model": "base",
            "sample_rate": 16000,
            "microphone_device": None,
            "language": None,
            "auto_start": False,
            "close_behavior": "ask",
        }

        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
                logger.info(f"Default configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save default configuration: {e}")

        return default_config

    def save_config(self):
        """Save current config to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def _set_windows_startup(self, enable: bool):
        """
        Add or remove app from Windows startup

        Args:
            enable: Whether to enable startup
        """
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                if enable:
                    # Get path to this script
                    script_path = Path(__file__).resolve()
                    python_exe = Path(sys.executable)
                    command = f'"{python_exe}" "{script_path}"'
                    winreg.SetValueEx(key, "fnwispr", 0, winreg.REG_SZ, command)
                    logger.info("Added fnwispr to Windows startup")
                else:
                    try:
                        winreg.DeleteValue(key, "fnwispr")
                        logger.info("Removed fnwispr from Windows startup")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            logger.error(f"Failed to set Windows startup: {e}")

    def normalize_key(self, key) -> Optional[object]:
        """
        Normalize modifier keys to handle left/right variants
        Only normalizes if the base key (not the specific variant) is in the hotkey combo.

        Args:
            key: Key to normalize

        Returns:
            Normalized key if applicable, otherwise the original key
        """
        if (
            key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r
        ) and keyboard.Key.ctrl in self.hotkey_combo:
            return keyboard.Key.ctrl
        elif (
            key == keyboard.Key.alt_l or key == keyboard.Key.alt_r
        ) and keyboard.Key.alt in self.hotkey_combo:
            return keyboard.Key.alt
        elif (
            key == keyboard.Key.shift_l or key == keyboard.Key.shift_r
        ) and keyboard.Key.shift in self.hotkey_combo:
            return keyboard.Key.shift
        else:
            return key

    def parse_hotkey(self, hotkey_string: str) -> set:
        """
        Parse hotkey string into a set of keys

        Args:
            hotkey_string: String like "ctrl+alt", "ctrl+win", "ctrl_l+win", etc.

        Returns:
            Set of keyboard.Key or keyboard.KeyCode objects
        """
        key_mapping = {
            "ctrl": keyboard.Key.ctrl,
            "ctrl_l": keyboard.Key.ctrl_l,
            "ctrl_r": keyboard.Key.ctrl_r,
            "alt": keyboard.Key.alt,
            "alt_l": keyboard.Key.alt_l,
            "alt_r": keyboard.Key.alt_r,
            "shift": keyboard.Key.shift,
            "shift_l": keyboard.Key.shift_l,
            "shift_r": keyboard.Key.shift_r,
            "cmd": keyboard.Key.cmd,
            "win": keyboard.Key.cmd,
        }

        keys = set()
        for part in hotkey_string.lower().split('+'):
            part = part.strip()
            if part in key_mapping:
                keys.add(key_mapping[part])
            elif len(part) == 1:
                keys.add(keyboard.KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key: {part}")

        return keys

    def audio_callback(self, indata, frames, time_info, status):
        """
        Callback for audio recording

        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Time information
            status: Stream status
        """
        if status:
            logger.warning(f"Audio stream status: {status}")

        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        """Start audio recording"""
        if not self.recording:
            logger.info("Started recording...")
            self.recording = True
            self.audio_data = []

            # Get microphone device
            device = self.config.get("microphone_device")

            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    callback=self.audio_callback,
                    device=device
                )
                self.stream.start()
            except Exception as e:
                logger.error(f"Failed to start audio recording: {e}")
                self.recording = False

    def stop_recording(self):
        """Stop audio recording and process the audio"""
        if self.recording:
            logger.info("Stopped recording")
            self.recording = False

            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")

            # Process the recorded audio in a separate thread to avoid blocking
            threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        """Process recorded audio and insert transcribed text"""
        if not self.audio_data:
            logger.warning("No audio data recorded")
            return

        temp_path = None
        try:
            # Concatenate audio data
            logger.debug(f"Audio chunks recorded: {len(self.audio_data)}")
            audio = np.concatenate(self.audio_data, axis=0)
            logger.debug(f"Audio shape: {audio.shape}, dtype: {audio.dtype}, min: {audio.min():.4f}, max: {audio.max():.4f}")

            # Create temporary file in system temp directory
            temp_dir = tempfile.gettempdir()
            temp_filename = f"fnwispr_audio_{uuid.uuid4().hex[:8]}.wav"
            temp_path = os.path.join(temp_dir, temp_filename)

            # Write audio data directly to file with error handling
            try:
                write_wav(temp_path, self.sample_rate, audio)
                logger.info(f"Audio saved to temporary file: {temp_path}")
            except Exception as write_err:
                logger.error(f"Failed to write WAV file: {write_err}")
                raise

            # Verify file exists immediately after writing
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                logger.debug(f"WAV file created successfully. Size: {file_size} bytes")
            else:
                raise FileNotFoundError(f"WAV file was not created at {temp_path}")

            # Give Windows filesystem time to flush
            time.sleep(0.1)

            # Send to local Whisper for transcription
            transcribed_text = self.transcribe_audio(temp_path)

            if transcribed_text:
                # Insert text at cursor position
                self.insert_text(transcribed_text)

        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)

        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    time.sleep(0.05)
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_path}: {e}")

    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file using local faster-whisper model

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text or None if failed
        """
        try:
            from scipy.io import wavfile

            language = self.config.get("language")

            logger.info(f"Transcribing audio file: {audio_path}")

            # Load audio directly using scipy to avoid ffmpeg dependency
            sample_rate_file, audio_data = wavfile.read(audio_path)
            logger.debug(f"Loaded audio: sample_rate={sample_rate_file}, shape={audio_data.shape}, dtype={audio_data.dtype}")

            # Convert to float32 and normalize (Whisper expects float32 in range [-1, 1])
            if audio_data.dtype != np.float32:
                audio_float = audio_data.astype(np.float32)
                if audio_data.dtype == np.int16:
                    audio_float = audio_float / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_float = audio_float / 2147483648.0
                elif audio_data.dtype == np.uint8:
                    audio_float = (audio_float - 128) / 128.0
            else:
                audio_float = audio_data

            # Ensure mono (if stereo, take first channel)
            if len(audio_float.shape) > 1:
                audio_float = audio_float[:, 0]

            logger.debug(f"Prepared audio: shape={audio_float.shape}, dtype={audio_float.dtype}, min={audio_float.min():.4f}, max={audio_float.max():.4f}")

            # faster-whisper returns (segments_generator, info)
            segments, info = self.whisper_model.transcribe(audio_float, language=language)

            # Collect all segment texts
            transcribed_text = " ".join(segment.text.strip() for segment in segments).strip()

            logger.info(f"Transcription successful. Language: {info.language} (probability: {info.language_probability:.2f})")
            logger.info(f"Transcribed text: {transcribed_text}")

            return transcribed_text

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"Transcription error: {e}")
            return None

    def insert_text(self, text: str):
        """
        Insert text at current cursor position

        Args:
            text: Text to insert
        """
        try:
            # Small delay to ensure the window is ready
            time.sleep(0.1)

            # Type the text
            pyautogui.typewrite(text, interval=0.01)
            logger.info(f"Text inserted: {text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to insert text: {e}")

    def on_press(self, key):
        """Keyboard press event handler"""
        try:
            # Normalize the key (handle left/right variants of modifiers)
            normalized_key = self.normalize_key(key)

            # Track currently pressed key
            self.current_keys.add(normalized_key)

            # Check if all hotkey keys are currently pressed
            if self.hotkey_combo.issubset(self.current_keys):
                self.start_recording()

        except Exception as e:
            logger.debug(f"Error in on_press: {e}")

    def on_release(self, key):
        """Keyboard release event handler"""
        try:
            # Normalize the key (handle left/right variants of modifiers)
            normalized_key = self.normalize_key(key)

            # Remove released key from tracking
            self.current_keys.discard(normalized_key)

            # Stop recording when any of the hotkey keys is released
            if normalized_key in self.hotkey_combo and self.recording:
                self.stop_recording()

            # Exit on Escape key
            if key == keyboard.Key.esc:
                logger.info("Escape pressed, shutting down...")
                self.is_running = False
                return False
        except Exception as e:
            logger.debug(f"Error in on_release: {e}")

    def _on_tray_settings(self):
        """Handle Settings click from tray"""
        if not self.settings_window:
            self.settings_window = SettingsWindow(
                self.config,
                on_close=self._on_settings_close,
                on_config_change=self._on_config_change,
                on_test_mic=self._test_microphone
            )
            try:
                self.settings_window.create_window()
            except Exception as e:
                logger.error(f"Cannot open settings window: {e}", exc_info=True)
                self.alert_manager.show_warning(
                    "Settings Window Unavailable",
                    "The settings window requires Tcl/Tk which is not installed.\n\n"
                    "HOW TO FIX:\n"
                    "1. Uninstall Python from Control Panel\n"
                    "2. Download Python from python.org\n"
                    "3. Run the installer\n"
                    "4. CHECK THE BOX: 'tcl/tk and IDLE'\n"
                    "5. Complete installation\n"
                    "6. Restart fnwispr\n\n"
                    "ALTERNATIVE (without Tcl/Tk):\n"
                    "• Edit config at: ~/.fnwispr/config.json\n"
                    "• Use tray menu to change:\n"
                    "  - Model (right-click → Model)\n"
                    "  - Microphone (right-click → Microphone)\n"
                    "• Hotkey still works normally"
                )
                self.settings_window = None
                return

        self.settings_window.show()

    def _on_settings_close(self):
        """Handle settings window close"""
        close_behavior = self.config.get("close_behavior", "ask")

        if close_behavior == "ask":
            choice = self.alert_manager.ask_quit_or_minimize()
            if choice == "quit":
                self.is_running = False
                self.settings_window.destroy()
            elif choice == "minimize":
                self.settings_window.hide()
        elif close_behavior == "minimize":
            self.settings_window.hide()
        elif close_behavior == "quit":
            self.is_running = False
            self.settings_window.destroy()

    def _on_config_change(self, new_config: dict):
        """Handle configuration change from GUI"""
        # Check if device changed
        old_device = self.config.get("microphone_device")
        new_device = new_config.get("microphone_device")

        if old_device != new_device:
            # Validate new device
            self.previous_device = old_device
            self.config = new_config
            self._init_microphone(is_startup=False)
            if self._get_device_name(new_device) != self._get_device_name(old_device):
                self.alert_manager.show_info(
                    "Microphone Changed",
                    f"Microphone changed to: {self._get_device_name(new_device)}"
                )
        else:
            self.config = new_config

        # Handle model change
        old_model = self.config.get("model", "base")
        new_model = new_config.get("model", "base")
        if old_model != new_model:
            self._load_whisper_model()

        # Handle hotkey change
        old_hotkey = self.config.get("hotkey")
        new_hotkey = new_config.get("hotkey")
        if old_hotkey != new_hotkey:
            self.hotkey_combo = self.parse_hotkey(new_hotkey)

        # Handle auto-start change
        old_auto_start = self.config.get("auto_start", False)
        new_auto_start = new_config.get("auto_start", False)
        if old_auto_start != new_auto_start:
            self._set_windows_startup(new_auto_start)

        self.config = new_config
        self.save_config()

    def _on_model_change(self, model: str):
        """Handle model change from tray menu"""
        if self.config.get("model") != model:
            self.config["model"] = model
            self._load_whisper_model()
            self.save_config()
            logger.info(f"Model changed to {model}")

    def _on_device_change(self, device_idx: Optional[int]):
        """Handle microphone device change from tray menu"""
        if self.config.get("microphone_device") != device_idx:
            self.previous_device = self.config.get("microphone_device")
            self.config["microphone_device"] = device_idx
            self._init_microphone(is_startup=False)
            self.save_config()
            logger.info(f"Microphone changed to {self._get_device_name(device_idx)}")

    def _test_microphone(self):
        """Test microphone initialization"""
        device_idx = self.config.get("microphone_device")
        device_name = self._get_device_name(device_idx)

        try:
            test_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=device_idx,
                blocksize=512
            )
            test_stream.start()
            time.sleep(0.5)
            test_stream.stop()
            test_stream.close()
            self.alert_manager.show_info("Microphone Test", f"✓ Microphone '{device_name}' is working!")
            logger.info("Microphone test successful")
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            self.alert_manager.show_mic_error(device_name, str(e), is_startup=False)

    def _keyboard_listener_thread(self):
        """Run keyboard listener in a thread"""
        try:
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            ) as listener:
                logger.info("Keyboard listener started. Ready to record!")
                while self.is_running:
                    time.sleep(0.1)
                logger.info("Keyboard listener stopped")
        except Exception as e:
            logger.error(f"Keyboard listener error: {e}")

    def run(self):
        """Run the client with GUI and keyboard listener"""
        logger.info("fnwispr starting...")

        # Check if first run
        is_first_run = not Path(self.config_path).exists()

        # Setup tray manager
        icon_path = str(Path(__file__).parent / "icons" / "app_icon.svg")
        self.tray_manager = TrayManager(
            icon_path=icon_path,
            on_settings=self._on_tray_settings,
            on_exit=lambda: setattr(self, 'is_running', False),
            on_model_change=self._on_model_change,
            on_device_change=self._on_device_change,
            get_current_model=lambda: self.config.get("model", "base"),
            get_current_device=lambda: self.config.get("microphone_device")
        )

        # Show settings on first run (but don't crash if Tkinter unavailable)
        if is_first_run:
            try:
                self._on_tray_settings()
            except Exception as e:
                logger.warning(f"Could not show settings window on first run: {e}")
                logger.info("Tcl/Tk may not be installed. Settings window will not be available.")

        # Start keyboard listener thread
        self.listener_thread = threading.Thread(target=self._keyboard_listener_thread, daemon=True)
        self.listener_thread.start()
        logger.info("Keyboard listener thread started")

        # Run tray (blocking)
        try:
            self.tray_manager.run()
        except Exception as e:
            logger.error(f"Tray manager error: {e}")

        logger.info("fnwispr stopped")


def main():
    """Main entry point"""
    try:
        client = FnwisprClient()
        client.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
