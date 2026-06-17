"""
Phone Agent - Vision Module (v3)
Multi-backend OCR: Google ML Kit (primary) + Tesseract (fallback).
Fuzzy text matching, text-to-coordinate mapping, interruption detection,
and template matching for icon-based UI elements.
All offline.
"""

import subprocess
import os
import requests
import numpy as np

# ============================================================
# 1. SCREENSHOT CAPTURE
# ============================================================

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


# ============================================================
# 2. OCR BACKENDS
# ============================================================

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


def mlkit_extract(image_path):
    """
    Send screenshot to local ML Kit service for text recognition.
    Requires ML Kit running as a service in Termux on localhost:8080.
    Returns structured text, or None if service unavailable.
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
            texts = []
            for block in data.get("textBlocks", []):
                for line in block.get("lines", []):
                    texts.append(line.get("text", ""))
            return "\n".join(texts)
        else:
            return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        print(f"ML Kit error: {e}")
        return None


def extract_text(image_path):
    """Try ML Kit first. If unavailable, fall back to Tesseract."""
    result = mlkit_extract(image_path)
    if result is not None:
        return result
    return tesseract_extract(image_path)


# ============================================================
# 3. FUZZY TEXT MATCHING
# ============================================================

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


# ============================================================
# 4. TEXT-TO-COORDINATE MAPPING
# ============================================================

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


def tap_coordinates(x, y):
    """Tap at specific screen coordinates via ADB."""
    subprocess.run(
        ["adb", "shell", "input", "tap", str(x), str(y)],
        capture_output=True,
        timeout=10
    )


# ============================================================
# 5. INTERRUPTION HANDLER
# ============================================================

INTERRUPTION_PATTERNS = [
    "incoming call", "accept", "decline",
    "update available", "update now", "later",
    "notification", "allow", "deny",
    "screen locked", "unlock"
]

def detect_interruption(image_path):
    """Scan screen for known interruption patterns."""
    screen_text = extract_text(image_path).lower()
    for pattern in INTERRUPTION_PATTERNS:
        if pattern in screen_text:
            return True
    return False


def dismiss_interruptions():
    """If an interruption is detected, dismiss it via back button."""
    import time
    for attempt in range(3):
        img = capture_screenshot("interrupt_check.png")
        if not img:
            return False
        if not detect_interruption(img):
            return True
        subprocess.run(
            ["adb", "shell", "input", "keyevent", "4"],
            capture_output=True,
            timeout=5
        )
        time.sleep(1.5)
    return False


# ============================================================
# 6. TEMPLATE MATCHING FOR ICON DETECTION (NEW - Day 7)
# ============================================================

def match_template(screenshot_path, template_path, threshold=0.8):
    """
    Find an icon/button on screen using template matching.
    
    Args:
        screenshot_path: Path to the current screen screenshot
        template_path: Path to the reference icon image (e.g., 'icons/send.png')
        threshold: Confidence threshold (0-1). Default 0.8 (80%).
    
    Returns:
        (x, y) center coordinates of the matched region, or None if no match.
    """
    try:
        import cv2
        
        screenshot = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        
        if screenshot is None or template is None:
            return None
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            print(f"  Icon matched at ({center_x}, {center_y}) with confidence {max_val:.2f}")
            return (center_x, center_y)
        else:
            print(f"  Best match confidence {max_val:.2f} below threshold {threshold}")
            return None
            
    except ImportError:
        return _simple_template_match(screenshot_path, template_path, threshold)
    except Exception as e:
        print(f"Template matching error: {e}")
        return None


def _simple_template_match(screenshot_path, template_path, threshold=0.8):
    """
    Lightweight template matching using only NumPy and PIL.
    Less accurate than OpenCV but has zero dependencies beyond NumPy.
    """
    try:
        from PIL import Image
        
        screenshot = Image.open(screenshot_path).convert("L")
        template = Image.open(template_path).convert("L")
        
        screenshot_arr = np.array(screenshot, dtype=np.float32)
        template_arr = np.array(template, dtype=np.float32)
        
        sh, sw = screenshot_arr.shape
        th, tw = template_arr.shape
        
        if th > sh or tw > sw:
            return None
        
        best_match = 0
        best_loc = (0, 0)
        
        for y in range(0, sh - th, 5):
            for x in range(0, sw - tw, 5):
                region = screenshot_arr[y:y+th, x:x+tw]
                diff = region - template_arr
                score = 1.0 - (np.mean(np.abs(diff)) / 255.0)
                
                if score > best_match:
                    best_match = score
                    best_loc = (x, y)
        
        if best_match >= threshold:
            center_x = best_loc[0] + tw // 2
            center_y = best_loc[1] + th // 2
            print(f"  Icon matched (simple) at ({center_x}, {center_y}) confidence {best_match:.2f}")
            return (center_x, center_y)
        else:
            return None
            
    except ImportError:
        print("PIL/Pillow not installed. Cannot run simple template matching.")
        return None
    except Exception as e:
        print(f"Simple template match error: {e}")
        return None


# ============================================================
# 7. TEST
# ============================================================

if __name__ == "__main__":
    print("Phone Agent - Vision Module v3")
    print("Backends: ML Kit (primary) + Tesseract (fallback)")
    print("Features: Fuzzy matching + Interruption detection + Template matching")
    
    img = capture_screenshot()
    if img:
        text = extract_text(img)
        print(f"Extracted {len(text)} characters.")
        print(f"First 100 chars: {text[:100]}...")
