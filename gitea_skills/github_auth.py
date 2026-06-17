#!/usr/bin/env python3
"""Helper script to manage GitHub authentication tokens securely in the macOS Keychain."""

import subprocess
import getpass
import sys
import platform
from pathlib import Path

# Add parent directory to sys.path to allow importing from gitea_skills when run directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitea_skills.core import _load_env

ACCOUNT = "token"

def get_service_name() -> str:
    """Get the project-scoped Keychain service name."""
    try:
        env = _load_env()
        repo = env.get("REPO_NAME")
        if repo:
            return f"gitea-skills-github-{repo}"
    except Exception:
        pass
    return "friendly-davinci-github"

def check_keychain():
    if platform.system() != "Darwin":
        return None
    
    service = get_service_name()
    # 1. Try project-scoped service first
    try:
        res = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", ACCOUNT, "-w"],
            capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        pass

    # 2. Fall back to legacy global service
    if service != "friendly-davinci-github":
        try:
            res = subprocess.run(
                ["security", "find-generic-password", "-s", "friendly-davinci-github", "-a", ACCOUNT, "-w"],
                capture_output=True, text=True, check=True
            )
            return res.stdout.strip()
        except subprocess.CalledProcessError:
            pass

    return None

def save_keychain(token):
    if platform.system() != "Darwin":
        return False
    service = get_service_name()
    try:
        subprocess.run(
            ["security", "add-generic-password", "-s", service, "-a", ACCOUNT, "-w", token, "-U"],
            check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error saving to macOS Keychain: {e.stderr}", file=sys.stderr)
        return False

def main():
    token = check_keychain()
    if token:
        print("Credentials loaded successfully from macOS Keychain.", file=sys.stderr)
        sys.exit(0)
        
    print("No GitHub credentials found in macOS Keychain.", file=sys.stderr)
    print("Please enter your GitHub Personal Access Token (PAT):", file=sys.stderr)
    token = getpass.getpass(prompt="GitHub Token: ")
    token = token.strip()
    
    if not token:
        print("Error: Token cannot be empty.", file=sys.stderr)
        sys.exit(1)
        
    if save_keychain(token):
        print("GitHub token saved securely in macOS Keychain.", file=sys.stderr)
    else:
        print("Warning: Could not save credentials securely to Keychain.", file=sys.stderr)

if __name__ == "__main__":
    main()
