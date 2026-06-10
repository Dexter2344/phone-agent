"""
Phone Agent - Vision Module
Handles screenshot capture, OCR text extraction,
and text-to-coordinate mapping. All offline.
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


def find_text_location(image_path, target_text):
    """Find the bounding box coordinates of target text in an image."""
    try:
        # Generate TSV output with bounding box data
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
        
        # Parse TSV for target text
        for line in lines[1:]:  # Skip header
            parts = line.strip().split("\t")
            if len(parts) >= 12:
                text = parts[11].strip().lower()
                if target_text.lower() in text:
                    # Return center coordinates
                    x = (int(parts[6]) + int(parts[8])) // 2
                    y = (int(parts[7]) + int(parts[9])) // 2
                    return (x, y)
        
        return None
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


# Test
if __name__ == "__main__":
    print("Phone Agent - Vision Module")
    print("Capturing screenshot...")
    img = capture_screenshot()
    if img:
        print(f"Screenshot saved: {img}")
        text = extract_text(img)
        print(f"Extracted {len(text)} characters.")
    else:
        print("Screenshot failed.")
