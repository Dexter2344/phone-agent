"""
Phone Agent - Vision Module (v5)
Primary: Android UI Hierarchy Inspection (uiautomator dump).
Fallback: ML Kit OCR + Tesseract OCR + Template Matching.
Verification: Numeric data validation for financial information.
"""

import subprocess
import os
import xml.etree.ElementTree as ET
import requests
import numpy as np
import time
import re

# ============================================================
# 1. UI HIERARCHY INSPECTION (PRIMARY)
# ============================================================

def get_ui_tree():
    """Dump the current screen's UI hierarchy using uiautomator."""
    try:
        subprocess.run(
            ["adb", "shell", "uiautomator", "dump", "/sdcard/ui_tree.xml"],
            capture_output=True, text=True, timeout=15
        )
        subprocess.run(
            ["adb", "pull", "/sdcard/ui_tree.xml", "ui_tree.xml"],
            capture_output=True, text=True, timeout=10
        )
        if os.path.exists("ui_tree.xml"):
            tree = ET.parse("ui_tree.xml")
            return tree.getroot()
        return None
    except Exception as e:
        print(f"UI tree error: {e}")
        return None


def find_element_by_description(root, description):
    """Search the UI tree for an element with a matching content-desc."""
    if root is None:
        return None
    for node in root.iter("node"):
        content_desc = node.get("content-desc", "")
        if description.lower() in content_desc.lower():
            return node
    return None


def find_element_by_text(root, text):
    """Search the UI tree for an element with matching text."""
    if root is None:
        return None
    for node in root.iter("node"):
        node_text = node.get("text", "")
        if text.lower() in node_text.lower():
            return node
    return None


def find_element_by_class(root, class_name):
    """Search the UI tree for the first element with a matching class."""
    if root is None:
        return None
    for node in root.iter("node"):
        if class_name in node.get("class", ""):
            return node
    return None


def get_element_bounds(node):
    """Extract the center coordinates from an element's bounds attribute."""
    if node is None:
        return None
    bounds_str = node.get("bounds", "")
    try:
        parts = bounds_str.replace("[", "").replace("]", ",").split(",")
        left = int(parts[0])
        top = int(parts[1])
        right = int(parts[2])
        bottom = int(parts[3])
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return (center_x, center_y)
    except:
        return None


def find_element_center(root, identifier):
    """Find an element by description first, then by text. Returns center coordinates."""
    node = find_element_by_description(root, identifier)
    if node is not None:
        print(f"  Found '{identifier}' by content-desc")
        return get_element_bounds(node)
    node = find_element_by_text(root, identifier)
    if node is not None:
        print(f"  Found '{identifier}' by text")
        return get_element_bounds(node)
    return None


# ============================================================
# 2. SCREENSHOT CAPTURE (FALLBACK)
# ============================================================

def capture_screenshot(filename="screen.png"):
    """Take a screenshot using ADB and save it locally."""
    try:
        result = subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            capture_output=True, timeout=15
        )
        with open(filename, "wb") as f:
            f.write(result.stdout)
        return filename
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None


# ============================================================
# 3. OCR BACKENDS (FALLBACK)
# ============================================================

def tesseract_extract(image_path):
    """Run Tesseract OCR on an image. Returns extracted text."""
    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "Tesseract not installed."
    except Exception as e:
        return f"Tesseract error: {e}"


def mlkit_extract(image_path):
    """Send screenshot to local ML Kit service. Returns structured text or None."""
    try:
        with open(image_path, "rb") as f:
            files = {"image": f}
            response = requests.post(
                "http://localhost:8080/text", files=files, timeout=10
            )
        if response.status_code == 200:
            data = response.json()
            texts = []
            for block in data.get("textBlocks", []):
                for line in block.get("lines", []):
                    texts.append(line.get("text", ""))
            return "\n".join(texts)
        return None
    except:
        return None


def extract_text(image_path):
    """Try ML Kit first. If unavailable, fall back to Tesseract."""
    result = mlkit_extract(image_path)
    if result is not None:
        return result
    return tesseract_extract(image_path)


# ============================================================
# 4. FUZZY TEXT MATCHING (FALLBACK)
# ============================================================

def levenshtein_distance(s1, s2):
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
# 5. TEXT-TO-COORDINATE VIA OCR (FALLBACK)
# ============================================================

def find_text_location(image_path, target_text):
    try:
        output_base = "ocr_output"
        subprocess.run(
            ["tesseract", image_path, output_base, "tsv"],
            capture_output=True, timeout=30
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
    except:
        return None


def tap_coordinates(x, y):
    """Tap at specific screen coordinates via ADB."""
    subprocess.run(
        ["adb", "shell", "input", "tap", str(x), str(y)],
        capture_output=True, timeout=10
    )


# ============================================================
# 6. TEMPLATE MATCHING (LAST RESORT FALLBACK)
# ============================================================

def match_template(screenshot_path, template_path, threshold=0.8):
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
            return (center_x, center_y)
        return None
    except ImportError:
        return _simple_template_match(screenshot_path, template_path, threshold)
    except:
        return None


def _simple_template_match(screenshot_path, template_path, threshold=0.8):
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
            return (center_x, center_y)
        return None
    except:
        return None


# ============================================================
# 7. INTERRUPTION HANDLER
# ============================================================

INTERRUPTION_PATTERNS = [
    "incoming call", "accept", "decline",
    "update available", "update now", "later",
    "notification", "allow", "deny",
    "screen locked", "unlock"
]

def detect_interruption(image_path):
    screen_text = extract_text(image_path).lower()
    for pattern in INTERRUPTION_PATTERNS:
        if pattern in screen_text:
            return True
    return False


def dismiss_interruptions():
    for attempt in range(3):
        img = capture_screenshot("interrupt_check.png")
        if not img:
            return False
        if not detect_interruption(img):
            return True
        subprocess.run(
            ["adb", "shell", "input", "keyevent", "4"],
            capture_output=True, timeout=5
        )
        time.sleep(1.5)
    return False


# ============================================================
# 8. UNIFIED TARGET FINDER (PRIMARY + FALLBACKS)
# ============================================================

def find_target(target):
    """
    Find a target on screen and return its center coordinates.
    Tries UI tree first, then OCR, then template matching.
    """
    root = get_ui_tree()
    if root is not None:
        coords = find_element_center(root, target)
        if coords is not None:
            print(f"  UI tree: Found '{target}' at {coords}")
            return coords
        else:
            print(f"  UI tree: '{target}' not found. Trying OCR...")
    else:
        print("  UI tree unavailable. Trying OCR...")
    
    img = capture_screenshot("target_search.png")
    if img:
        coords = find_text_location(img, target)
        if coords is not None:
            print(f"  OCR: Found '{target}' at {coords}")
            return coords
        else:
            print(f"  OCR: '{target}' not found. Trying template matching...")
    else:
        print("  Screenshot failed. Trying template matching...")
    
    icon_path = f"{target.lower().replace(' ', '_')}.png"
    if os.path.exists(icon_path):
        img = capture_screenshot("template_search.png")
        if img:
            coords = match_template(img, icon_path)
            if coords is not None:
                print(f"  Template match: Found '{target}' at {coords}")
                return coords
    
    print(f"  All methods failed to find '{target}'")
    return None


# ============================================================
# 9. NUMERIC VERIFICATION FOR FINANCIAL DATA (NEW - Day 17)
# ============================================================

def verify_financial_data():
    """
    Verify that extracted text contains valid financial data.
    Uses double-read confirmation, format validation, and range checking.
    
    Returns:
        (is_valid: bool, extracted_value: str, confidence: str)
    """
    # Capture and read twice
    img1 = capture_screenshot("verify_finance_1.png")
    if not img1:
        return False, "", "Screenshot failed"
    text1 = extract_text(img1)
    
    img2 = capture_screenshot("verify_finance_2.png")
    if not img2:
        return False, "", "Screenshot failed"
    text2 = extract_text(img2)
    
    # Extract numbers from both readings
    pattern = r'[₦$£€]?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
    
    matches1 = re.findall(pattern, text1)
    matches2 = re.findall(pattern, text2)
    
    if not matches1 or not matches2:
        return False, "", "No currency values found"
    
    def clean_number(num_str):
        return num_str.replace('₦', '').replace('$', '').replace('£', '').replace('€', '').replace(',', '').strip()
    
    num1 = clean_number(matches1[0])
    num2 = clean_number(matches2[0])
    
    # Compare readings
    if num1 == num2:
        try:
            value = float(num1)
            if 1 <= value <= 1000000000:
                return True, matches1[0], "High confidence (double-read match)"
            else:
                return False, matches1[0], "Value out of reasonable range"
        except ValueError:
            return False, num1, "Cannot parse as number"
    
    # Reads differ. Try a third time.
    print("  Verification: Reads differ. Trying third capture...")
    img3 = capture_screenshot("verify_finance_3.png")
    if not img3:
        return True, matches1[0], "Low confidence (reads differed, no tiebreaker)"
    
    text3 = extract_text(img3)
    matches3 = re.findall(pattern, text3)
    
    if not matches3:
        return True, matches1[0], "Low confidence (reads differed, third failed)"
    
    num3 = clean_number(matches3[0])
    
    # Best of three
    if num1 == num3:
        return True, matches1[0], "Medium confidence (2 of 3 match)"
    elif num2 == num3:
        return True, matches2[0], "Medium confidence (2 of 3 match)"
    else:
        return True, matches1[0], "Very low confidence (all 3 reads differ)"


# ============================================================
# 10. TEST
# ============================================================

if __name__ == "__main__":
    print("Phone Agent - Vision Module v5")
    print("Primary: UI Tree | Fallback: ML Kit + Tesseract + Template Matching")
    print("Verification: Numeric data validation for financial information")
    
    root = get_ui_tree()
    if root is not None:
        print("UI tree captured successfully.")
        coords = find_target("Send")
        if coords:
            print(f"Found target at {coords}")
    else:
        print("UI tree failed. Falling back to screenshot OCR.")
