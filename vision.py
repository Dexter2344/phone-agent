"""
Phone Agent - Vision Module (v2)
Handles screenshot capture, OCR text extraction,
fuzzy text matching, and text-to-coordinate mapping.
All offline.
"""

import subprocess
import os

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


def extract_text(image_path):
    """Run Tesseract OCR on an image and return extracted text."""
    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "Tesseract not installed. Run: pkg install tesseract"
    except Exception as e:
        return f"OCR error: {e}"


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


def find_text_location(image_path, target_text):
    """Find bounding box coordinates of target text using fuzzy matching."""
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


if __name__ == "__main__":
    print("Phone Agent - Vision Module v2 (with Fuzzy Matching)")
    img = capture_screenshot()
    if img:
        print(f"Screenshot saved: {img}")
        text = extract_text(img)
        print(f"Extracted {len(text)} characters.")
