"""
Phone Agent - Day 10
Natural language → Gemma 4 → ADB commands.
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

def ask_ollama(prompt):
    """Send a prompt to the local Gemma 4 model."""
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
    """Execute an ADB command and return output."""
    try:
        result = subprocess.run(
            command.split(), capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"ADB error: {str(e)}"

def parse_command(user_input):
    """Ask Gemma 4 to break a natural language command into steps."""
    prompt = f"""You are a phone automation agent. Break this command into steps.
Each step: open_app, tap, type, swipe, or wait.
Command: {user_input}
Respond in JSON: {{"steps": [{{"action": "...", "target": "..."}}]}}
JSON:"""
    response = ask_ollama(prompt)
    try:
        return json.loads(response)
    except:
        return {"error": "Could not parse steps", "raw": response}

def verify_action(expected_text):
    """Take a screenshot and verify expected text appeared."""
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
    """Execute a single step using UI tree, OCR, and template matching fallbacks."""
    action = step.get("action", "")
    target = step.get("target", "")

    if action == "open_app":
        run_adb(f"adb shell monkey -p com.{target.lower()} -c android.intent.category.LAUNCHER 1")
        time.sleep(2)
        if verify_action(target[:5]):
            return True, f"Opened {target}"
        else:
            run_adb(f"adb shell monkey -p com.{target.lower()} -c android.intent.category.LAUNCHER 1")
            time.sleep(2)
            return verify_action(target[:5]), f"Opened {target} (retry)"

    elif action == "tap":
        dismiss_interruptions()
        coords = find_target(target)
        if coords:
            tap_coordinates(coords[0], coords[1])
            time.sleep(1)
            if verify_action(target[:5]):
                return True, f"Tapped {target}"
            return False, f"Tapped {target} but verification failed"
        return False, f"Could not find {target} on screen"

    elif action == "type":
        run_adb(f'adb shell input text "{target}"')
        return True, f"Typed: {target}"

    elif action == "wait":
        seconds = int(target) if target.isdigit() else 2
        time.sleep(seconds)
        return True, f"Waited {seconds}s"

    return False, f"Unknown action: {action}"

def run_task(user_command):
    """Full pipeline: parse, execute, verify."""
    print(f"\nTask: {user_command}")
    print("-" * 40)
    plan = parse_command(user_command)
    if "error" in plan:
        print(f"Parse error: {plan['error']}")
        return
    steps = plan.get("steps", [])
    print(f"Plan: {len(steps)} steps")
    for i, step in enumerate(steps):
        print(f"\nStep {i+1}: {step.get('action')} → {step.get('target')}")
        success, message = execute_step(step)
        status = "✅" if success else "❌"
        print(f"  {status} {message}")
        if not success:
            print("Task aborted.")
            return
    print("\n✅ Task completed.")

if __name__ == "__main__":
    print("Phone Agent v10 - UI Tree Vision")
    print("ADB:", run_adb("adb devices"))
    print("Ollama:", ask_ollama("Say 'ready'"))
