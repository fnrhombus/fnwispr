# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fnwispr is a **unified Windows speech-to-text application** with local processing:
- **Single Application**: Windows-only Python application (`client/main.py`)
- **No Server Component**: All speech recognition happens locally using OpenAI's Whisper
- **System Tray GUI**: Graphical interface for configuration and control
- **Local Processing**: Everything runs on the user's machine without external services

## Branching & Releases

**Branching model**:
- **`dev`** is the main development branch. All work happens here.
- **`main`** is the release branch. **Never commit directly to main.**
- Merging `dev` → `main` triggers the release workflow automatically.

**Versioning** follows **Semantic Versioning** (semver.org). The single source of truth is the root `VERSION` file.

- **MAJOR** (X.0.0): Breaking changes to user-facing behavior or configuration format
- **MINOR** (0.X.0): New features, new settings, new GUI elements
- **PATCH** (0.0.X): Bug fixes, performance improvements, internal refactors

**Release rules**:
- Bump `VERSION` on `dev` before merging to `main`
- `client/setup.py` and `client/main.py` both read from `VERSION` automatically
- The release workflow reads `VERSION`, creates the `vX.Y.Z` tag, builds the installer, and publishes a draft GitHub Release
- If the tag already exists, the workflow skips (no duplicate releases)
- Pre-1.0: minor bumps may include breaking changes

**Architecture Highlights**:
1. Windows global hotkeys (via `pynput`)
2. System audio devices (via `sounddevice`)
3. Host OS keyboard input simulation (via `pyautogui`)
4. Local Whisper model for transcription
5. System tray icon with context menu
6. Tkinter-based settings window

## Development Commands

### Build & Run

```bash
# Install dependencies
pip install -r client/requirements.txt
pip install -r requirements-dev.txt  # for development

# Run the application
python client/main.py

# Or use VS Code task: "Run: fnwispr"

# Run with debugger
# Use VS Code: F5 to debug, or task "Debug: fnwispr"
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=client --cov-report=html

# Or use VS Code tasks: "Test: All Tests", "Test: Coverage Report"
```

### New Modules

**GUI Components** (added for system tray integration):
- `client/gui.py` - Tkinter settings window with tabs for Recording, Model, and General settings
- `client/tray.py` - System tray icon with context menu for quick access (pystray)
- `client/alerts.py` - Alert dialogs for user notifications (messagebox)

**Key Features**:
- System tray icon in bottom-right with context menu
- Double-click or right-click → Settings to open configuration window
- Quick model selection from tray menu without opening settings
- Quick microphone device selection from tray menu
- Microphone error alerts on startup and configuration changes
- First-run setup wizard
- Configuration auto-migration from old location to `~/.fnwispr/config.json`

### Linting & Formatting

```bash
# Format code with Black (line length: 120)
black client/ server/

# Check with Flake8
flake8 client/ server/ --max-line-length=120 --ignore=E203,W503

# Or use VS Code task: "Lint: All"
```

### Docker Operations

```bash
# View server logs
docker-compose logs -f whisper-service

# Check service health
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/models

# Clean Docker (removes volumes)
docker-compose down -v --remove-orphans
```

## Architecture Details

### Client Architecture (client/main.py)

The `FnwisprClient` class implements a state machine:

1. **Initialization**: Loads config, parses hotkey combo into a set of `pynput.keyboard.Key` objects
2. **Keyboard Listening**: Uses `pynput.keyboard.Listener` with custom press/release handlers
3. **Hotkey Detection**: Maintains `current_keys` set; recording starts when `hotkey_combo.issubset(current_keys)`
4. **Audio Recording**: `sounddevice.InputStream` with callback appending chunks to `audio_data` list
5. **Processing**: On release, spawns thread to avoid blocking keyboard listener:
   - Concatenates NumPy audio chunks
   - Writes temporary WAV file (16kHz, mono)
   - POSTs to `/transcribe` endpoint with file + model name
   - Deletes temp file
6. **Text Insertion**: Uses `pyautogui.typewrite()` to simulate keyboard input at cursor position

**Key implementation detail**: The keyboard listener is monkey-patched to track currently pressed keys, enabling hotkey combo detection.

### Server Architecture (server/main.py)

FastAPI application with **global model cache**:

- `model` and `current_model_name` globals prevent reloading
- `load_model()` function checks if model needs changing before calling `whisper.load_model()`
- Models are cached by Whisper in `~/.cache/whisper` (mounted as Docker volume)
- Startup event loads default model from `WHISPER_MODEL` env var

**Endpoints**:
- `POST /transcribe`: Accepts multipart/form-data with `audio` file, `model_name`, optional `language`
- `GET /health`: Returns model status
- `GET /models`: Lists available models with descriptions
- `GET /`: API info

**Transcription flow**:
1. Save uploaded file to temp location (preserves extension for FFmpeg)
2. Call `whisper_model.transcribe(temp_path, language=...)`
3. Extract text and detected language from result dict
4. Clean up temp file in `finally` block
5. Return JSON response

### Configuration System

**Client config** (`client/config.json`):
- Created automatically from defaults if missing
- Supports hotkey parsing (e.g., "ctrl+alt", "ctrl+shift+a")
- `microphone_device`: `null` uses default, or integer device ID from `sounddevice.query_devices()`
- `language`: `null` for auto-detect, or ISO language code

**Server config** (environment variables):
- `WHISPER_MODEL`: Model to load on startup (tiny/base/small/medium/large)
- Set via `.env` file or docker-compose environment

### VS Code Integration

**Pre-configured tasks** (`.vscode/tasks.json`):
- Build, run, test, utility, lint categories
- Default build: "Build: All Docker Services"
- Default test: "Test: All Tests"
- Notable compound tasks: "Dev: Setup Project", "Dev: Rebuild and Restart"

**Debug configurations** (`.vscode/launch.json`):
- "Debug: Client" - includes preLaunchTask for server health check
- "Debug: Server (Local)" - runs server via uvicorn with reload
- "Debug: Full Stack (Client + Server)" - compound configuration
- "Debug: Attach to Docker Server" - requires debugpy on port 5678 (not implemented yet)

## Whisper Model Selection

Performance vs accuracy tradeoff:

| Model  | Size  | Speed    | VRAM   | Recommendation |
|--------|-------|----------|--------|----------------|
| tiny   | 39M   | 32x      | ~1GB   | Testing only   |
| base   | 74M   | 16x      | ~1GB   | Default choice |
| small  | 244M  | 6x       | ~2GB   | Better accuracy|
| medium | 769M  | 2x       | ~5GB   | High accuracy  |
| large  | 1550M | 1x (ref) | ~10GB  | Best quality   |

Change model via:
1. Client config: `"model": "small"` (per-request selection)
2. Server env: `WHISPER_MODEL=small` (startup default)

## Client Architecture Details

### Main Application Flow

1. **Initialization** (`FnwisprClient.__init__`)
   - Load config from `~/.fnwispr/config.json` (auto-migrate from old location)
   - Load Whisper model
   - Initialize microphone with error handling
   - Parse hotkey configuration

2. **Startup** (`FnwisprClient.run`)
   - Check if first run (show settings window if true)
   - Start keyboard listener in background thread
   - Initialize system tray icon with SVG icon conversion
   - Show tray menu with Model and Microphone submenus
   - Run event loop (blocking)

3. **Recording Flow**
   - Global keyboard listener detects hotkey combo
   - `on_press` tracks currently pressed keys
   - When all hotkey keys pressed: `start_recording()` begins audio stream
   - `on_release` stops recording when any hotkey key released
   - Audio chunks collected via sounddevice callback
   - `process_audio()` runs in separate thread (non-blocking)

4. **Audio Processing**
   - Concatenate audio chunks from multiple callbacks
   - Write to temporary WAV file
   - Load with scipy (avoids ffmpeg dependency)
   - Normalize to float32 in [-1, 1] range
   - Convert stereo to mono if needed
   - Pass to Whisper.transcribe()
   - Clean up temp file
   - Insert text with pyautogui if transcription succeeds

### Configuration Management

- **Location**: `~/.fnwispr/config.json` (user profile directory)
- **Auto-Migration**: Old `./config.json` auto-migrated on first run with new fields
- **Fields**:
  - `hotkey`: String like "ctrl+win", "ctrl_l+alt", supports all pynput modifiers
  - `model`: Whisper size (tiny/base/small/medium/large)
  - `sample_rate`: 16000 recommended
  - `microphone_device`: null for default, or device index from sounddevice
  - `language`: null for auto-detect, or ISO code like "en", "es", "fr"
  - `auto_start`: Windows registry auto-start at login
  - `close_behavior`: "ask"/"minimize"/"quit" when closing settings

### Microphone Error Handling

**On Startup**:
- Try to initialize audio stream with configured device
- If fails: Show alert with device name and error details
- App continues running (user can fix via Settings or tray menu)
- Tray tooltip shows error state

**On Config Change**:
- Save previous working device as fallback
- Try to initialize new device
- If fails: Show alert with revert message
- Revert config to fallback device
- Reinitialize with fallback

**Test Feature**:
- Settings window has "Test Microphone" button
- Creates short audio stream and validates it works
- Shows success or error alert

### System Tray Integration

**Icon Handling**:
- Source: `client/icons/app_icon.svg`
- Converted to PNG at runtime using cairosvg
- Fallback: Generated simple icon if SVG conversion fails

**Context Menu**:
- Settings (opens GUI, or minimizes from tray)
- Model submenu: Radio buttons for all 5 model sizes
- Microphone submenu: Dynamically populated from sounddevice.query_devices()
- Exit

**Threading**:
- Tray icon runs in blocking event loop (main thread)
- Keyboard listener runs in daemon background thread
- GUI events (settings, config changes) run in separate threads
- All config changes thread-safe (GIL prevents race conditions)

### GUI Implementation

**Settings Window** (`gui.py`):
- Tkinter TTkNotebook with 3 tabs
- Recording: Hotkey, microphone, language, test button
- Model: Radio buttons with info display
- General: Auto-start, close behavior, view logs

**Alerts** (`alerts.py`):
- Tkinter messageboxes for errors/warnings
- Microphone-specific error messages for startup vs config change
- Ask quit/minimize dialog with optional "remember choice"

**Tray Manager** (`tray.py`):
- pystray for cross-platform tray support
- Regenerates menu on open to reflect current device list
- Callbacks for menu items run in separate threads

## Common Development Patterns

### Adding a new API endpoint

1. Add Pydantic model in `server/main.py` if needed
2. Implement endpoint function with FastAPI decorators
3. Use logger for info/error messages
4. Handle exceptions and return appropriate HTTPException
5. Update API docs section in README.md

### Modifying client behavior

1. Client state lives in `FnwisprClient` instance variables
2. Audio processing happens in separate thread (don't block keyboard listener)
3. Always clean up temp files in `finally` blocks
4. Log to `fnwispr_client.log` for debugging
5. Test with actual Windows hotkeys (can't be fully mocked)

### Adding configuration options

1. Update `create_default_config()` in `client/main.py`
2. Update `config.example.json`
3. Document in README.md Configuration Options table
4. Update PRD.md section 4.1.5 if it's a functional requirement

## Important Implementation Notes

### Audio Format
- Client records 16kHz mono WAV (Whisper's native input)
- scipy.io.wavfile used for WAV writing (not wave module)
- Temporary files preserve original extension for FFmpeg compatibility

### Error Handling
- Client continues running even if transcription fails (logs error)
- Server returns 500 with error message but doesn't crash
- Network errors during POST are caught and logged

### Thread Safety
- Audio processing spawned in daemon thread to avoid blocking
- `audio_data` list appended to from callback thread (NumPy arrays are thread-safe)
- No locks needed in current implementation (single recording at a time)

### Platform-Specific Code
- `pyautogui.typewrite()` simulates keyboard on Windows (uses Windows API under the hood)
- Some Windows apps may block automated input (security feature)
- ESC key exits client (global listener pattern)

## Testing Strategy

Currently minimal tests (see README.md "TODO: Add tests").

**When implementing tests**:
- Mock `pynput`, `sounddevice`, `pyautogui` for client unit tests
- Use `TestClient` from FastAPI for server API tests
- Integration tests should use `tiny` model (fastest)
- Consider pytest fixtures for Docker service setup/teardown

## PRD Maintenance

When adding features:
1. Update `docs/PRD.md` with new functional requirements (FR-X.Y format)
2. Add to appropriate release version section (13.1, 13.2, etc.)
3. Update architecture section if system components change
4. Follow existing FR numbering scheme
