---
name: Streaming STT Research
description: Research findings on enabling real-time streaming transcription in fnwispr — library options, architectural approaches, and difficulty assessment
type: project
---

## Current Architecture (Batch Mode)

fnwispr currently uses `openai-whisper` (PyTorch) in a batch pipeline:
1. Hold hotkey → sounddevice InputStream accumulates audio chunks into a list
2. Release hotkey → chunks concatenated, written to temp WAV, entire file transcribed by Whisper
3. Full transcription typed out via pyautogui

**Key bottleneck**: No text appears until the user releases the hotkey AND the full recording is transcribed.

## Streaming Library Options (Researched April 2026)

### Tier 1: Most Relevant for fnwispr

| Library | Stars | Latest Release | Approach | Latency |
|---------|-------|---------------|----------|---------|
| **faster-whisper** (SYSTRAN) | 21.9k | v1.2.1 (Oct 2025) | CTranslate2 backend, lazy generator, 4x speed, built-in VAD filter | N/A (building block) |
| **RealtimeSTT** (KoljaB) | 9.6k | v0.3.104 (May 2025) | WebRTCVAD + SileroVAD + faster-whisper; `feed_audio()` accepts external PCM | 0.5-1.5s after speech |

### Tier 2: Worth Knowing

| Library | Stars | Notes |
|---------|-------|-------|
| **whisper_streaming** (UFAL) | 3.6k | Local agreement policy, ~3.3s latency, being replaced by SimulStreaming |
| **SimulStreaming** (UFAL) | 548 | Successor, won IWSLT 2025, ~0.7s latency, research-oriented |
| **WhisperLive** (Collabora) | 3.9k | Client-server WebSocket architecture — adds server component, against fnwispr design |
| **WhisperX** | 21.1k | Batch only — no streaming, but excellent for alignment/diarization |

### Not Viable
- **openai-whisper** itself has zero streaming support (reads entire file, 30s sliding window)

## Three Possible Approaches

### Approach A: Replace openai-whisper with faster-whisper (Minimal Change)
- Swap the backend for 4x speed improvement + lazy segment generator
- Keep the same push-to-talk batch flow
- Text arrives faster but still only after release
- **Difficulty: Low** — mostly API surface change
- **Streaming: No** — but significantly reduces perceived latency

### Approach B: Chunked streaming with faster-whisper + Silero VAD (DIY)
- While hotkey held, periodically send accumulated audio to faster-whisper
- Use Silero VAD to detect natural speech pauses for chunk boundaries
- Emit partial transcriptions progressively (type text while still recording)
- On release, do a final pass on any remaining audio
- **Difficulty: Medium-High** — new threading model, partial text management, text correction/replacement
- **Key challenge**: How to handle text that was already typed but gets revised by later context

### Approach C: Integrate RealtimeSTT (Drop-in Library)
- Replace sounddevice + whisper pipeline with RealtimeSTT's `AudioToTextRecorder`
- Use `feed_audio()` to pipe existing sounddevice chunks, or let it manage its own mic
- VAD + faster-whisper handled internally; callbacks for partial/final text
- **Difficulty: Medium** — library does the heavy lifting but integration with existing tray/GUI/hotkey system needs work
- **Risk**: Original author stepped back; community-maintained. 119 open issues.

## Key Technical Challenges for Any Streaming Approach

1. **Text revision problem**: Early transcriptions of partial audio may be wrong; later context corrects them. How to handle already-typed text that needs correction? (backspace + retype? placeholder?)
2. **pyautogui interaction**: Currently types character-by-character. Streaming means interleaving typing with ongoing recording — thread safety with target application focus.
3. **Model swap**: All streaming libraries use faster-whisper (CTranslate2), not openai-whisper (PyTorch). This is a required dependency change regardless of approach.
4. **GPU/CUDA**: faster-whisper needs CUDA 12 + cuDNN 9 for GPU. CPU mode works but is slower.
5. **Hotkey interaction model**: Push-to-talk naturally segments audio — may not need VAD at all if we just chunk on time intervals while held.

## Why: User exploring feasibility of making transcription feel more responsive
## How to apply: Use this research when planning the streaming implementation — start with Approach A (fastest win) and evaluate if Approach B or C is needed
