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
- Element detection now works across different devices without reference
- - Accessibility audit completed for 15 popular Android apps
- Scoring system created: A (fully automatable) to F (completely inaccessible)
- WhatsApp & Google apps score A. Local banking/government apps score D or F.
- Public accessibility score list in development
- Multi-app workflows supported via task memory system
- Agent can switch between apps and carry data across them
- First multi-app task completed: copy bank balance → send via WhatsApp
  

 ## Accessibility Audit

## Accessibility Audit

The Phone Agent doubles as an accessibility tester. Apps with rich UI labels are automatable. Apps without labels are invisible to both AI agents and screen readers.

**Methodology:**
- Each app was tested using `adb shell uiautomator dump` to extract the UI hierarchy XML.
- The XML was parsed for `content-desc` attributes on interactive elements (buttons, inputs, icons).
- Apps were scored based on the percentage of interactive elements with meaningful labels.

**Scoring System:**
| Score | Criteria |
|-------|----------|
| **A** | 90%+ of interactive elements have meaningful `content-desc` labels. Fully automatable. Fully accessible to screen readers. |
| **B** | 70-89% labeled. Mostly automatable. Minor gaps. |
| **C** | 50-69% labeled. Partially automatable. Relies on OCR fallback. |
| **D** | 10-49% labeled. Mostly blind. Heavy OCR dependency. |
| **F** | <10% labeled. Completely inaccessible to both AI and screen readers. |

**Audit Results (30 Apps Tested):**

| App | Category | Score | Notes |
|-----|----------|-------|-------|
| WhatsApp | Messaging | **A** | Excellent labels. Every button, input, and icon labeled. |
| Telegram | Messaging | **A** | Strong accessibility. Content descriptions throughout. |
| Google Messages | Messaging | **A** | Full label coverage. |
| Gmail | Email | **A** | Comprehensive labels on all actions. |
| Outlook | Email | **A** | Good label coverage. |
| Google Maps | Navigation | **A** | Excellent labels on UI elements. |
| Waze | Navigation | **A** | Strong labeling. |
| Slack | Productivity | **B** | Good labels. Some dynamic elements unlabeled. |
| Notion | Productivity | **B** | Mostly labeled. Some custom UI elements missing descriptions. |
| Google Calendar | Productivity | **A** | Full label coverage. |
| Spotify | Music | **B** | Good labels on controls. Some album art unlabeled. |
| Uber Eats | Food Delivery | **B** | Most elements labeled. Some promotional cards missing. |
| Deliveroo | Food Delivery | **B** | Similar to Uber Eats. Minor gaps. |
| Duolingo | Education | **A** | Excellent accessibility. Designed for broad access. |
| Khan Academy | Education | **A** | Strong labeling throughout. |
| Banking App A | Banking | **F** | No labels. All buttons have empty `content-desc`. |
| Banking App B | Banking | **F** | No labels. Completely invisible to screen readers. |
| Banking App C | Banking | **F** | No labels. Generic class names only. |
| Banking App D | Banking | **F** | No labels. |
| Banking App E | Banking | **F** | No labels. |
| Government App A | Government | **F** | No labels. Login form unlabeled. |
| Government App B | Government | **F** | No labels. All elements generic. |
| Government App C | Government | **F** | No labels. |
| Government App D | Government | **F** | No labels. |
| Local Food App A | Food Delivery | **D** | Minimal labels. Only header text found. |
| Local Food App B | Food Delivery | **D** | Few labels. Most buttons unlabeled. |
| Local Education App A | Education | **D** | Some labels. Navigation mostly unlabeled. |
| Local Health App A | Health | **D** | Minimal labels. Critical buttons unlabeled. |
| Local Health App B | Health | **F** | No labels. |
| Telecom App A | Telecom | **D** | Few labels. Account actions unlabeled. |

**Key Findings:**
- 100% of global messaging apps scored A.
- 100% of banking apps scored F.
- 100% of government apps scored F.
- The accessibility divide is not technical—it's a priority gap.
- Numeric verification layer for financial data: format check, double-read, range validation
- Banking app OCR accuracy improved from 80% to 94%
- Agent double-checks its own work before storing financial data

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
