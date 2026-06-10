# Phone Agent

An autonomous AI agent that controls an Android phone. Runs entirely offline using Gemma 4, Termux, and ADB. No cloud. No API keys. No data leaving your device.

## What It Does

- Takes natural language commands ("Open WhatsApp and message Mom")
- Parses commands into step-by-step plans using local Gemma 4
- Executes phone actions via ADB (open apps, tap, type, swipe)
- Everything runs locally on the phone

## Tech Stack

| Component | Tool |
|-----------|------|
| AI Model | Gemma 4 E4B (via Ollama) |
| Runtime | Termux (Linux on Android) |
| Phone Control | ADB + Android UI Automator |
| Orchestration | Python |

## Current Status

🚧 Early development. Core script is working. Screen detection and multi-step verification are in progress.
- Screen text detection (OCR) via Tesseract is working


## How It Works

1. User gives a command in plain English
2. Gemma 4 parses it into structured steps (JSON)
3. Python script translates steps into ADB commands
4. Agent executes each step and verifies the result
5. All processing happens on-device. No internet required.

## Setup (Coming Soon)

Full setup guide will be added as the project matures.

## Build Log

This project is being built in public on Dev.to. Follow the journey:
- [Project Log #1: Introduction](https://dev.to/okeke_chukwudubem_5f3bf49)
- [Project Log #2: Repo & First Script](link to today's post)

## Author

**Okeke Chukwudubem**
- GitHub: [Dexter2344](https://github.com/Dexter2344)
- Dev.to: [@okeke_chukwudubem](https://dev.to/okeke_chukwudubem_5f3bf49)
- Substack: [Okeke Chukwudubem](https://open.substack.com/pub/okekechukwudubem1)

## License

MIT
