"""
Phone Agent - Day 15
Natural language → Gemma 4 → ADB commands.
Multi-app workflows with task memory.
Vision: UI tree primary, OCR + template matching fallback.
"""

import requests
import subprocess
import json
import time
import os
from vision import (
    capture_screenshot, extract_text, find_target,
    tap_coordinates, dismiss_interruptions
)

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "gemma4:4b"

# ── Task Memory (NEW - Day 15) ──
task_memory = {}

def remember(key, value):
    """Store a value in task memory."""
    task_memory[key] = value
    print(f"  Memory: Stored '{key}' = '{value}'")

def recall(key):
    """Retrieve a value from task memory."""
    return task_memory.get(key, None)

def clear_memory():
    """Clear all task memory."""
    task_memory.clear()
    print("  Memory: Cleared")

def ask_ollama(prompt):
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
    try:
        result = subprocess.run(
            command.split(), capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"ADB error: {str(e)}"

def go_home():
    """Return to home screen between app switches."""
    run_adb("adb shell input keyevent KEYCODE_HOME")
    time.sleep(1)

def parse_command(user_input):
    prompt = f"""You are a phone automation agent. Break this command into steps.
Each step: open_app, tap, type, read_screen, switch_app, remember, recall, swipe, or wait.
For multi-app tasks, use 'remember' to store values and 'recall' to retrieve them.
Command: {user_input}
Respond in JSON: {{"steps": [{{"action": "...", "target": "..."}}]}}
JSON:"""
    response = ask_ollama(prompt)
    try:
        return json.loads(response)
    except:
        return {"error": "Could not parse steps", "raw": response}

def verify_action(expected_text):
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

def execute_step(step):
    action = step.get("action", "")
    target = step.get("target", "")

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

    elif action == "switch_app":
        go_home()
        run_adb(f"adb shell monkey -p com.{target.lower()} -c android.intent.category.LAUNCHER 1")
        time.sleep(2)
        return True, f"Switched to {target}"

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

    elif action == "type":
        # Check if target is a memory key
        value = recall(target)
        text_to_type = value if value else target
        run_adb(f'adb shell input text "{text_to_type}"')
        return True, f"Typed: {text_to_type}"

    elif action == "read_screen":
        img = capture_screenshot("read_screen.png")
        if img:
            text = extract_text(img)
            return True, text
        return False, "Could not read screen"

    elif action == "remember":
        # The previous step's output is passed as the target
        return True, f"Remembered: {target}"

    elif action == "recall":
        value = recall(target)
        if value:
            return True, value
        return False, f"No value stored for '{target}'"

    elif action == "wait":
        seconds = int(target) if target.isdigit() else 2
        time.sleep(seconds)
        return True, f"Waited {seconds}s"

    return False, f"Unknown action: {action}"

def run_task(user_command):
    print(f"\nTask: {user_command}")
    print("-" * 40)
    clear_memory()
    plan = parse_command(user_command)
    if "error" in plan:
        print(f"Parse error: {plan['error']}")
        return
    steps = plan.get("steps", [])
    print(f"Plan: {len(steps)} steps")
    
    for i, step in enumerate(steps):
        action = step.get("action", "")
        target = step.get("target", "")
        print(f"\nStep {i+1}: {action} → {target}")
        
        if action == "remember":
            # Store the target value in memory
            remember(target, target)
            print(f"  ✅ Stored '{target}'")
            continue
        
        if action == "recall":
            value = recall(target)
            if value:
                print(f"  ✅ Recalled '{target}' = '{value}'")
            else:
                print(f"  ❌ No value for '{target}'")
            continue
        
        success, message = execute_step(step)
        
        # If this was a read_screen, store the result
        if action == "read_screen" and success:
            extracted = message
            print(f"  ✅ Read: {extracted[:100]}...")
            # Auto-store for next step if needed
            if i + 1 < len(steps) and steps[i+1].get("action") == "remember":
                remember(steps[i+1].get("target"), extracted.strip())
                success = True
                message = "Read and stored"
        else:
            status = "✅" if success else "❌"
            print(f"  {status} {message}")
        
        if not success:
            print("Task aborted.")
            return
    
    print("\n✅ Multi-app task completed.")

if __name__ == "__main__":
    print("Phone Agent v15 - Multi-App Workflows")
    print("ADB:", run_adb("adb devices"))
    print("Ollama:", ask_ollama("Say 'ready'"))
