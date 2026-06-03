#!/usr/bin/env python3
"""Helper script to manage GitHub authentication tokens securely in the macOS Keychain."""

import subprocess
import getpass
import sys
import platform

SERVICE = "friendly-davinci-github"
ACCOUNT = "token"

def check_keychain():
    if platform.system() != "Darwin":
        return None
    try:
        res = subprocess.run(
            ["security", "find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w"],
            capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def save_keychain(token):
    if platform.system() != "Darwin":
        return False
    try:
        subprocess.run(
            ["security", "add-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w", token, "-U"],
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
