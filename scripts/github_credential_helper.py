#!/usr/bin/env python3
"""Custom Git credential helper to securely provide credentials from the macOS Keychain."""

import sys
import subprocess
import platform

SERVICE = "friendly-davinci-github"
ACCOUNT = "token"

def get_token():
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

def main():
    # Git calls the helper with 'get', 'store', or 'erase'
    if len(sys.argv) < 2 or sys.argv[1] != "get":
        sys.exit(0)
        
    # Read request details from stdin (protocol=https, host=github.com, etc.)
    # We consume stdin to avoid broken pipe issues.
    _ = sys.stdin.read()
    
    token = get_token()
    if token:
        # Return credentials to Git via stdout
        print("username=oauth2")
        print(f"password={token}")

if __name__ == "__main__":
    main()
