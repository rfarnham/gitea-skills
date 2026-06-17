#!/usr/bin/env python3
"""Custom Git credential helper to securely provide credentials from the macOS Keychain."""

import sys
import subprocess
import platform
from pathlib import Path

# Add parent directory to sys.path to allow importing from gitea_skills when run directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitea_skills.github_auth import check_keychain

def get_token():
    return check_keychain()

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
