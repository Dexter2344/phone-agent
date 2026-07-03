# Phone Agent

An autonomous AI agent that controls an Android phone. Runs entirely offline using Gemma 4, Termux, and ADB. No cloud. No API keys. No data leaving your device.

## What It Does

- Takes natural language commands ("Open WhatsApp and message Mom")
- Parses commands into step-by-step plans using local Gemma 4
- Executes phone actions via ADB (open apps, tap, type, swipe)
- Reads screen text via ML Kit (primary) and Tesseract (fallback)
- Detects icons and image-only buttons via template matching
- Handles interruptions (calls, notifications, dialogs)
- Verifies each step before moving to the next
- Everything runs locally on the phone

## Tech Stack

| Component | Tool |
|-----------|------|
| AI Model | Gemma 4 E4B (via Ollama) |
| Runtime | Termux (Linux on Android) |
| Phone Control | ADB + Android UI Automator |
| OCR (Text) | Google ML Kit (primary) + Tesseract (fallback) |
| Icon Detection | OpenCV template matching (primary) + NumPy/PIL (fallback) |
| Orchestration | Python |

## Current Status

- ML Kit integration: screen scans 5x faster (1.5-2s vs 8-12s)
- Interruption handler: dismisses calls, notifications, dialogs before tasks
- Multi-backend vision: ML Kit primary, Tesseract fallback
- Template matching wired into agent as OCR fallback
- Icon library: send_button.png, back_button.png, search_button.png
- Full pipeline test passed: open WhatsApp → find contact → type → detect send icon → tap → verify
- - UI hierarchy inspection added as primary vision method
- Unified target finder: UI tree → OCR → template matching
- Element detection now works across different devices without reference images

## How It Works

1. User gives a command in plain English
2. Gemma 4 parses it into structured steps (JSON)
3. Python script translates steps into ADB commands
4. Agent captures screenshot and reads screen via ML Kit/Tesseract
5. If target is text → OCR finds coordinates
6. If target is an icon → template matching finds coordinates
7. Agent executes each step and verifies the result
8. All processing happens on-device. No internet required.

## Setup (Coming Soon)

Full setup guide will be added as the project matures.

## Build Log

This project is being built in public on Dev.to. Follow the journey:
- [Project Log #1: Introduction](https://dev.to/okeke_chukwudubem_5f3bf49)
- Daily updates posted on Dev.to under the `#buildinpublic` tag

## Icon Library

| Icon | File | App | Status |
|------|------|-----|--------|
| Send button | `send_button.png` | WhatsApp | ✅ Working |
| Back button | `back_button.png` | WhatsApp | ✅ Working |
| Search button | `search_button.png` | WhatsApp | 🔧 Testing |

## Author

**Okeke Chukwudubem**
- GitHub: [Dexter2344](https://github.com/Dexter2344)
- Dev.to: [@okeke_chukwudubem](https://dev.to/okeke_chukwudubem_5f3bf49)
- Substack: [Okeke Chukwudubem](https://open.substack.com/pub/okekechukwudubem1)
- X (Twitter): [@OkekeDD](https://x.com/OkekeDD)

## License

MIT
