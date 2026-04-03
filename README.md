# fnwispr

> Speech-to-text anywhere on Windows with a hotkey

fnwispr is a Windows speech-to-text tool that lets you dictate text in any application using a simple hotkey. Press and hold Ctrl+Win (configurable), speak, release, and your words appear as text - powered by OpenAI's Whisper running locally on your machine.

## Features

- **Universal Text Input**: Works in any Windows application that accepts text
- **Simple Hotkey**: Press and hold to record, release to transcribe
- **System Tray Integration**: Runs silently in the system tray with easy access menu
- **GUI Settings**: Graphical interface for all configuration options
- **Quick Model Selection**: Change Whisper model size directly from tray menu
- **Quick Microphone Selection**: Switch microphone devices from tray menu without opening settings
- **Privacy-First**: All processing happens locally on your machine
- **High Accuracy**: Powered by OpenAI's Whisper speech recognition
- **Multi-Language**: Supports 99+ languages with automatic detection
- **Configurable**: Choose your hotkey, model size, language, and microphone via GUI
- **No Internet Required**: Works completely offline once models are downloaded
- **Windows Integration**: Auto-start at login, graceful error alerts for audio issues

## Architecture

fnwispr is a unified application that runs entirely on your Windows machine:
- **Hotkey Detection**: Uses `pynput` to detect global keyboard shortcuts
- **Audio Recording**: Captures audio from your microphone using `sounddevice`
- **Speech Recognition**: Uses OpenAI's Whisper model loaded locally
- **Text Insertion**: Simulates keyboard input with `pyautogui`
- **No External Services**: Everything runs on your machine

## Installation

Download the latest installer from the [Releases page](https://github.com/fnrhombus/fnwispr/releases):

1. Download **`fnwispr-x.y.z-setup.exe`** from the latest release
2. Run the installer — no admin rights required
3. Launch fnwispr from the Start Menu or desktop shortcut

The installer bundles everything (Python, Whisper, dependencies), so there's nothing else to install. The first launch downloads your selected Whisper model, which may take a minute.

> **Coming soon**: `winget install fnrhombus.fnwispr`

### Prerequisites

- Windows 10 or 11 (64-bit)
- A working microphone

## Quick Start

### Usage

#### First Run
When you run fnwispr for the first time, a settings window automatically opens. Configure your preferences:
- **Recording**: Set your hotkey, select microphone, choose language
- **Model**: Select Whisper model size (base recommended for most users)
- **General**: Enable/disable auto-start at login, set close behavior

#### Daily Usage
1. Start the application - it minimizes to the system tray
2. Look for the fnwispr icon in your system tray (bottom-right corner)
3. **To use the hotkey**:
   - Open any application where you want to type (e.g., Notepad, Word, browser)
   - Click to place your cursor where you want text inserted
   - Press and hold **Ctrl+Win** (or your configured hotkey)
   - Speak clearly into your microphone
   - Release the hotkey when done speaking
   - Wait a moment for transcription (depends on model size)
   - Your spoken words appear as text at the cursor

#### Tray Menu
Right-click the fnwispr icon in the system tray for quick access:
- **Settings...** - Open full settings window (or double-click icon)
- **Model >** - Change Whisper model size without opening settings
- **Microphone >** - Switch microphone device without opening settings
- **Exit** - Quit the application

#### Troubleshooting
- **Microphone not working?** Right-click tray icon → Microphone > and select a different device, or open Settings and click "Test Microphone"
- **Wrong model selected?** Right-click tray icon → Model > and pick a different size
- **Close to tray, quit, or ask?** Edit in Settings → General tab

**Press ESC to exit the application (only while keyboard listener is active)**

## Configuration

Configuration is managed through the GUI (recommended) or by editing `~/.fnwispr/config.json`:

```json
{
  "hotkey": "ctrl+win",
  "model": "base",
  "sample_rate": 16000,
  "microphone_device": null,
  "language": null,
  "auto_start": false,
  "close_behavior": "ask"
}
```

### Configuration Options

| Option | Description | Default | Options |
|--------|-------------|---------|---------|
| `hotkey` | Key combination to activate recording | `"ctrl+win"` | `"ctrl+alt"`, `"ctrl+win"`, `"ctrl_l+win"`, etc. |
| `model` | Whisper model size | `"base"` | `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large"` |
| `sample_rate` | Audio sample rate | `16000` | `16000` recommended |
| `microphone_device` | Microphone to use | `null` (default) | `null` for default, or device index number |
| `language` | Force specific language | `null` (auto-detect) | `"en"`, `"es"`, `"fr"`, `"de"`, etc. |
| `auto_start` | Start fnwispr at Windows login | `false` | `true` or `false` |
| `close_behavior` | Action when closing settings window | `"ask"` | `"ask"`, `"minimize"` (to tray), `"quit"` |

### Configuration File Location
- **Windows**: `C:\Users\YourUsername\.fnwispr\config.json`
- Configuration is automatically created on first run
- If you have an old `client/config.json`, it's automatically migrated to the new location

### Hotkey Configuration

The `hotkey` option supports flexible key combinations:

**Modifier keys (both left and right work):**
- `ctrl` - Either left or right Ctrl
- `alt` - Either left or right Alt
- `shift` - Either left or right Shift
- `win` or `cmd` - Windows/Command key

**Specific variants (if you want only left or right):**
- `ctrl_l`, `ctrl_r` - Left or right Ctrl specifically
- `alt_l`, `alt_r` - Left or right Alt specifically
- `shift_l`, `shift_r` - Left or right Shift specifically

**Examples:**
- `"ctrl+win"` - Either Ctrl + either Windows key (recommended)
- `"ctrl+alt"` - Either Ctrl + either Alt
- `"ctrl_l+win"` - Only left Ctrl + either Windows key
- `"alt_r+shift"` - Only right Alt + either Shift
- `"ctrl+shift+a"` - Either Ctrl + either Shift + 'a' key

### Whisper Model Selection

Choose the model that best fits your needs:

| Model | Size | Speed | Accuracy | VRAM | Best For |
|-------|------|-------|----------|------|----------|
| `tiny` | 39M | Fastest | Good | ~1GB | Quick testing, low-end systems |
| `base` | 74M | Fast | Better | ~1GB | **Recommended for most users** |
| `small` | 244M | Medium | Great | ~2GB | Better accuracy needed |
| `medium` | 769M | Slow | Excellent | ~5GB | High accuracy required |
| `large` | 1550M | Slowest | Best | ~10GB | Maximum accuracy |

To change the model, update the `model` field in `config.json` and restart the client.

## Finding Your Microphone Device

To list available audio devices:

```python
import sounddevice as sd
print(sd.query_devices())
```

Look for your microphone in the output and note its device ID number. Add it to `config.json`:

```json
{
  "microphone_device": 1
}
```

## Troubleshooting

### No audio being recorded

**Problem**: Transcription returns empty or no text appears

**Solutions**:
1. Check your microphone is connected and working
2. Verify microphone isn't muted in Windows settings
3. Try specifying `microphone_device` explicitly in config (see above)
4. Check client logs in `fnwispr_client.log`

### Slow transcription

**Problem**: Takes too long to transcribe

**Solutions**:
1. Use a smaller model (`tiny` or `base`)
2. Speak shorter phrases (under 30 seconds)
3. Close other applications to free up resources
4. Consider GPU acceleration (requires NVIDIA GPU and configuration)

### Text appears in wrong place

**Problem**: Text inserts somewhere unexpected

**Solutions**:
1. Make sure the target application is focused when you release the hotkey
2. Wait for transcription to complete before clicking elsewhere
3. Some applications may not accept automated text input

### Model download is slow

**Problem**: First-time setup taking a long time

**Solutions**:
- First download can take several minutes depending on model size and internet speed
- The model is cached, so subsequent starts are much faster
- Try starting with `tiny` or `base` model for faster initial setup

## Development

### Local Development Setup

1. **Install VS Code Extensions**
   - Press `Ctrl+Shift+X` to open Extensions
   - Install recommended extensions (especially **Python** by Microsoft)
   - Or click "Install All" when VS Code prompts for workspace recommendations

2. **Initialize Environment**
   ```powershell
   .\init.ps1
   ```
   This creates a virtual environment and installs all dependencies.

3. **Start Development**
   - Press `F5` to debug the application
   - Press `Ctrl+Shift+P` → "Tasks: Run Task" to run development tasks
   - See `.vscode/SETUP.md` for detailed VS Code configuration

### Available Development Tasks

- `Dev: Initialize Environment` - Setup venv and install dependencies
- `Build: Install Dependencies` - Install/reinstall packages
- `Run: fnwispr` - Run the application
- `Test: All Tests` - Run test suite
- `Lint: All` - Format and lint code
- `Utility: View Application Logs` - Monitor live logs

### Running Tests

```bash
# TODO: Add tests
pytest
```

### Project Structure

```
fnwispr/
├── client/              # Main application
│   ├── main.py         # Application entry point with hotkey, audio, and Whisper
│   ├── config.example.json  # Example configuration
│   └── requirements.txt  # Dependencies
├── tests/               # Test suite
├── docs/                # Documentation
│   └── PRD.md          # Product Requirements Document
├── .vscode/             # VS Code configuration
│   ├── tasks.json      # Development tasks
│   ├── launch.json     # Debug configurations
│   └── SETUP.md        # Setup guide
├── init.ps1            # Development environment initialization
├── requirements-dev.txt # Development tools
├── .gitignore
└── README.md
```

## How It Works

1. **Startup**: Application loads your configured Whisper model on startup (may take a moment)
2. **Hotkey Detection**: Uses `pynput` to detect when your configured hotkey combination is pressed
3. **Audio Recording**: While the hotkey is held, `sounddevice` captures audio from your microphone
4. **Audio Processing**: When released, the audio is saved as a temporary WAV file (16kHz, mono)
5. **Transcription**: The Whisper model processes the audio locally
6. **Text Insertion**: Uses `pyautogui` to type the transcribed text at the current cursor position
7. **Cleanup**: Temporary audio file is deleted

## Privacy & Security

- **Local Processing**: All audio processing happens on your computer
- **No Cloud**: No data is sent to external servers
- **Temporary Files**: Audio recordings are deleted immediately after transcription
- **No External Services**: Everything runs locally on your machine

## Limitations

- **Windows Only**: Application currently only supports Windows
- **Press-to-Transcribe**: No real-time streaming (must finish speaking before transcription)
- **Single Speaker**: Optimized for single-speaker dictation
- **First-Time Load**: Model download and initialization on first run can take a few minutes

## Roadmap

See [docs/PRD.md](docs/PRD.md) for detailed feature roadmap.

**Upcoming features**:
- Visual recording indicator
- GPU acceleration support
- Real-time streaming transcription

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - The amazing speech recognition model
- [pynput](https://github.com/moses-palmer/pynput) - Keyboard hotkey detection
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Audio recording
- [pyautogui](https://pyautogui.readthedocs.io/) - Keyboard automation for text input

## Support

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/fnrhombus/fnwispr/issues)
- **Documentation**: See [docs/](docs/) for detailed documentation
- **FAQ**: Check the Troubleshooting section above

---

**Made with speech-to-text** (obviously!)
