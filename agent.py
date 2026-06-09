"""
Phone Agent - Day 1
A Python script that takes a natural language command,
parses it via Gemma 4 (local Ollama), and executes
phone actions via ADB.
"""

import requests
import subprocess
import json

# Configuration
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
        else:
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

def parse_command(user_input):
    """Ask Gemma 4 to break a natural language command into steps."""
    prompt = f"""You are a phone automation agent. Break the following user command into a sequence of simple steps. Each step should be a single phone action: open_app, tap, type, swipe, or wait.

User command: {user_input}

Respond in JSON format:
{{"steps": [{{"action": "open_app", "target": "app_name"}}, {{"action": "tap", "target": "button_name"}}, ...]}}

JSON:"""
    response = ask_ollama(prompt)
    try:
        return json.loads(response)
    except:
        return {"error": "Could not parse steps", "raw": response}

# Test
if __name__ == "__main__":
    print("Phone Agent - Ready")
    print("Testing ADB connection...")
    print(run_adb("adb devices"))
    print("\nTesting Ollama connection...")
    print(ask_ollama("Say 'Hello from your phone agent.'"))
