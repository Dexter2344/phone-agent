"""
Phone Agent - Day 17
Natural language → Gemma 4 → ADB commands.
Multi-app workflows with task memory, home screen reset,
and numeric verification for financial data.
Vision: UI tree primary, OCR + template matching fallback.
"""

import requests
import subprocess
import json
import time
import os
from vision import (
    capture_screenshot, extract_text, find_target,
    tap_coordinates, dismiss_interruptions, verify_financial_data
)

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "gemma4:4b"

# ============================================================
# TASK MEMORY (Day 15)
# ============================================================
task_memory = {}

def remember(key, value):
    """Store a value in task memory for cross-app data transfer."""
    task_memory[key] = value
    print(f"  Memory: Stored '{key}' = '{value}'")

def recall(key):
    """Retrieve a value from task memory."""
    return task_memory.get(key, None)

def clear_memory():
    """Clear all task memory at the start of a new task."""
    task_memory.clear()


# ============================================================
# HOME SCREEN RESET (Day 16)
# ============================================================
def go_home():
    """
    Return to the home screen before switching apps.
    Prevents apps from resuming to the wrong screen.
    """
    subprocess.run(
        ["adb", "shell", "input", "keyevent", "KEYCODE_HOME"],
        capture_output=True, timeout=5
    )
    time.sleep(1)


# ============================================================
# AI & ADB HELPERS
# ============================================================
def ask_ollama(prompt):
    """Send a prompt to the local Gemma 4 model via Ollama API."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 256}
    }
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get("response", "No response.")
        return f"API error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def run_adb(command):
    """Execute an ADB command and return the output."""
    try:
        result = subprocess.run(
            command.split(), capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"ADB error: {str(e)}"


# ============================================================
# COMMAND PARSING
# ============================================================
def parse_command(user_input):
    """Ask Gemma 4 to break a natural language command into structured steps."""
    prompt = f"""You are a phone automation agent. Break this command into steps.
Each step: open_app, switch_app, tap, type, read_screen, remember, recall, swipe, or wait.
For multi-app tasks, use 'remember' to store values and 'recall' to retrieve them.
Command: {user_input}
Respond in JSON: {{"steps": [{{"action": "...", "target": "..."}}]}}
JSON:"""
    response = ask_ollama(prompt)
    try:
        return json.loads(response)
    except:
        return {"error": "Could not parse steps", "raw": response}


# ============================================================
# VERIFICATION
# ============================================================
def verify_action(expected_text):
    """Take a screenshot and verify that the expected text appeared on screen."""
    time.sleep(1)
    for attempt in range(3):
        img = capture_screenshot(f"verify_{attempt}.png")
        if not img:
            continue
        screen_text = extract_text(img)
        if expected_text.lower() in screen_text.lower():
            return True
        time.sleep(1)
    return False


# ============================================================
# STEP EXECUTION
# ============================================================
def execute_step(step):
    """
    Execute a single step.
    Returns (success: bool, message: str).
    """
    action = step.get("action", "")
    target = step.get("target", "")

    # ── Open App (fresh launch from home) ──
    if action == "open_app":
        go_home()
        run_adb(f"adb shell monkey -p com.{target.lower()} -c android.intent.category.LAUNCHER 1")
        time.sleep(2)
        if verify_action(target[:5]):
            return True, f"Opened {target}"
        else:
            run_adb(f"adb shell monkey -p com.{target.lower()} -c android.intent.category.LAUNCHER 1")
            time.sleep(2)
            return verify_action(target[:5]), f"Opened {target} (retry)"

    # ── Switch App (home reset + launch) ──
    elif action == "switch_app":
        go_home()
        run_adb(f"adb shell monkey -p com.{target.lower()} -c android.intent.category.LAUNCHER 1")
        time.sleep(2)
        return True, f"Switched to {target}"

    # ── Tap (with OCR/template fallback) ──
    elif action == "tap":
        dismiss_interruptions()
        coords = find_target(target)
        if coords:
            tap_coordinates(coords[0], coords[1])
            time.sleep(1)
            if verify_action(target[:5]):
                return True, f"Tapped {target}"
            return False, f"Tapped {target} but verification failed"
        return False, f"Could not find {target}"

    # ── Type (supports memory recall) ──
    elif action == "type":
        value = recall(target)
        text_to_type = value if value else target
        run_adb(f'adb shell input text "{text_to_type}"')
        return True, f"Typed: {text_to_type}"

    # ── Read Screen (OCR) ──
    elif action == "read_screen":
        img = capture_screenshot("read_screen.png")
        if img:
            text = extract_text(img)
            return True, text
        return False, "Could not read screen"

    # ── Wait ──
    elif action == "wait":
        seconds = int(target) if target.isdigit() else 2
        time.sleep(seconds)
        return True, f"Waited {seconds}s"

    return False, f"Unknown action: {action}"


# ============================================================
# FULL TASK PIPELINE
# ============================================================
def run_task(user_command):
    """
    Parse a natural language command, execute all steps,
    manage task memory, and verify financial data.
    """
    print(f"\n{'='*60}")
    print(f"Task: {user_command}")
    print(f"{'='*60}")
    
    clear_memory()
    go_home()
    
    plan = parse_command(user_command)
    if "error" in plan:
        print(f"Parse error: {plan['error']}")
        return
    
    steps = plan.get("steps", [])
    print(f"Plan: {len(steps)} steps\n")
    
    for i, step in enumerate(steps):
        action = step.get("action", "")
        target = step.get("target", "")
        print(f"Step {i+1}: {action} → {target}")
        
        # ── Handle memory actions ──
        if action == "remember":
            remember(target, target)
            print(f"  ✅ Stored '{target}'\n")
            continue
        
        if action == "recall":
            value = recall(target)
            if value:
                print(f"  ✅ Recalled '{target}' = '{value}'\n")
            else:
                print(f"  ❌ No value stored for '{target}'\n")
            continue
        
        # ── Execute the step ──
        success, message = execute_step(step)
        
        # ── Handle read_screen with financial verification ──
        if action == "read_screen" and success:
            extracted = message
            print(f"  ✅ Read: {extracted[:100]}...")
            
            # If next step is remember, check if it's financial data
            if i + 1 < len(steps) and steps[i+1].get("action") == "remember":
                key = steps[i+1].get("target", "")
                
                # Check for financial terms
                is_financial = any(
                    fin_term in key.lower() 
                    for fin_term in ["balance", "amount", "transaction", "payment", "₦", "$", "£", "salary", "debit", "credit", "account"]
                )
                
                if is_financial:
                    print(f"  🔍 Financial data detected. Running verification...")
                    is_valid, verified_value, confidence = verify_financial_data()
                    
                    if is_valid and verified_value:
                        remember(key, verified_value)
                        print(f"  ✅ Verified ({confidence}): {verified_value}\n")
                        success = True
                        message = f"Verified and stored: {verified_value}"
                    else:
                        print(f"  ❌ Verification failed: {confidence}\n")
                        success = False
                        message = f"Verification failed: {confidence}"
                else:
                    # Non-financial data. Store directly.
                    remember(key, extracted.strip())
                    print(f"  ✅ Stored non-financial data\n")
                    success = True
                    message = "Read and stored"
        else:
            status = "✅" if success else "❌"
            print(f"  {status} {message}\n")
        
        # Abort on failure
        if not success:
            print("Task aborted due to failure.")
            go_home()
            return
    
    go_home()
    print(f"\n{'='*60}")
    print("✅ Multi-app task completed.")
    print(f"{'='*60}\n")


# ============================================================
# STARTUP
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Phone Agent v17 — Numeric Verification + Multi-App")
    print("=" * 60)
    print("ADB:", run_adb("adb devices"))
    print("Ollama:", ask_ollama("Say 'ready'"))
    print("=" * 60)
