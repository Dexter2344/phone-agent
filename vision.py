"""
Phone Agent - Vision Module (v3)
Multi-backend OCR: Google ML Kit (primary) + Tesseract (fallback).
Includes fuzzy text matching and text-to-coordinate mapping.
All offline.
"""

import subprocess
import os
import requests

# ---- Tesseract OCR ----
def tesseract_extract(image_path):
    """Run Tesseract OCR on an image. Returns extracted text."""
    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "Tesseract not installed."
    except Exception as e:
        return f"Tesseract error: {e}"

# ---- ML Kit OCR (Primary, faster) ----
def mlkit_extract(image_path):
    """
    Send screenshot to local ML Kit service for text recognition.
    Requires ML Kit running as a service in Termux on localhost:8080.
    Returns structured text with bounding boxes, or None if service unavailable.
    """
    try:
        with open(image_path, "rb") as f:
            files = {"image": f}
            response = requests.post(
                "http://localhost:8080/text",
                files=files,
                timeout=10
            )
        if response.status_code == 200:
            data = response.json()
            # ML Kit returns blocks → lines → text
            texts = []
            for block in data.get("textBlocks", []):
                for line in block.get("lines", []):
                    texts.append(line.get("text", ""))
            return "\n".join(texts)
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None  # ML Kit service not running
    except Exception as e:
        print(f"ML Kit error: {e}")
        return None

# ---- Unified Extraction (Primary + Fallback) ----
def extract_text(image_path):
    """
    Try ML Kit first. If unavailable, fall back to Tesseract.
    Returns clean extracted text.
    """
    # Try ML Kit first (faster, more accurate)
    result = mlkit_extract(image_path)
    if result is not None:
        return result

    # Fall back to Tesseract
    return tesseract_extract(image_path)

# ---- Screenshot Capture ----
def capture_screenshot(filename="screen.png"):
    """Take a screenshot using ADB and save it locally."""
    try:
        result = subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=15
        )
        with open(filename, "wb") as f:
            f.write(result.stdout)
        return filename
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

# ---- Fuzzy Text Matching ----
def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance for fuzzy matching."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def fuzzy_match(target, candidate, threshold=0.8):
    """Check if candidate matches target within similarity threshold."""
    target_lower = target.lower().strip()
    candidate_lower = candidate.lower().strip()
    if target_lower == candidate_lower:
        return True
    if target_lower in candidate_lower or candidate_lower in target_lower:
        return True
    max_len = max(len(target_lower), len(candidate_lower))
    if max_len == 0:
        return True
    distance = levenshtein_distance(target_lower, candidate_lower)
    similarity = 1 - (distance / max_len)
    return similarity >= threshold

# ---- Text-to-Coordinate Mapping ----
def find_text_location(image_path, target_text):
    """Find coordinates of target text using Tesseract TSV output."""
    try:
        output_base = "ocr_output"
        subprocess.run(
            ["tesseract", image_path, output_base, "tsv"],
            capture_output=True,
            timeout=30
        )
        tsv_file = f"{output_base}.tsv"
        if not os.path.exists(tsv_file):
            return None
        with open(tsv_file, "r") as f:
            lines = f.readlines()
        best_match = None
        best_similarity = 0
        for line in lines[1:]:
            parts = line.strip().split("\t")
            if len(parts) >= 12:
                text = parts[11].strip()
                if fuzzy_match(target_text, text):
                    confidence = int(parts[10]) if parts[10].isdigit() else 50
                    if confidence > best_similarity:
                        best_similarity = confidence
                        x = (int(parts[6]) + int(parts[8])) // 2
                        y = (int(parts[7]) + int(parts[9])) // 2
                        best_match = (x, y)
        return best_match
    except Exception as e:
        print(f"Text location error: {e}")
        return None

# ---- Tap Coordinates ----
def tap_coordinates(x, y):
    """Tap at specific screen coordinates via ADB."""
    subprocess.run(
        ["adb", "shell", "input", "tap", str(x), str(y)],
        capture_output=True,
        timeout=10
    )

# ---- Interruption Handler (NEW) ----
INTERRUPTION_PATTERNS = [
    "incoming call", "accept", "decline",
    "update available", "update now", "later",
    "notification", "allow", "deny",
    "screen locked", "unlock"
]

def detect_interruption(image_path):
    """
    Scan screen for known interruption patterns.
    Returns True if an interruption is detected.
    """
    screen_text = extract_text(image_path).lower()
    for pattern in INTERRUPTION_PATTERNS:
        if pattern in screen_text:
            return True
    return False

def dismiss_interruptions():
    """
    If an interruption is detected, dismiss it.
    Presses back button and waits for UI to settle.
    """
    for attempt in range(3):
        img = capture_screenshot("interrupt_check.png")
        if not img:
            return False
        if not detect_interruption(img):
            return True  # No interruption found
        # Press back to dismiss
        subprocess.run(
            ["adb", "shell", "input", "keyevent", "4"],
            capture_output=True,
            timeout=5
        )
        import time
        time.sleep(1.5)
    return False  # Still interrupted after 3 attempts

# ---- Test ----
if __name__ == "__main__":
    print("Phone Agent - Vision Module v3")
    print("Backends: ML Kit (primary) + Tesseract (fallback)")

    # Test extraction
    img = capture_screenshot()
    if img:
        text = extract_text(img)
        print(f"Extracted {len(text)} characters.")
        print(f"First 100 chars: {text[:100]}...")
