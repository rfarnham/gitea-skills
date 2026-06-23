#!/usr/bin/env python3
"""Helper script to manage GitHub authentication tokens securely in the macOS Keychain."""

import subprocess
import getpass
import sys
import platform
import os
import urllib.request
import urllib.error
import json
from pathlib import Path

# Add parent directory to sys.path to allow importing from gitea_skills when run directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitea_skills.core import _load_env

ACCOUNT = "token"

def get_github_token(verbose=True) -> str:
    """Retrieve GitHub token using the priority sequence with validation and fallback.
    1. GITHUB_TOKEN or GITHUB_PAT environment variables.
    2. GITHUB_TOKEN or GITHUB_PAT in local project / global config.
    3. macOS Keychain fallback.
    """
    def try_token(token_val: str, source_name: str, delete_on_fail=None) -> str:
        if not token_val:
            return None
        token_val = token_val.strip()
        if verbose:
            print(f"Loading token from {source_name}...", file=sys.stderr)
        
        try:
            url = "https://api.github.com/user"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {token_val}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            })
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                username = data.get("login")
                if verbose:
                    print(f"Successfully authenticated as @{username}.", file=sys.stderr)
                return token_val
        except urllib.error.HTTPError as e:
            if e.code == 401:
                if verbose:
                    print(f"[Warning] Token from {source_name} is invalid (401).", file=sys.stderr)
                if delete_on_fail:
                    delete_on_fail()
                return None
            else:
                # Other HTTP errors (e.g. rate limit, 500, etc.): assume token is ok, network/server issue
                if verbose:
                    print(f"Token from {source_name} validation returned HTTP {e.code}. Proceeding without fallback.", file=sys.stderr)
                return token_val
        except Exception as e:
            # Network issue: assume token is ok
            if verbose:
                print(f"Token from {source_name} validation failed to connect ({e}). Proceeding without fallback.", file=sys.stderr)
            return token_val

    # 1. Environment variables
    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")
    if env_token:
        var_name = "GITHUB_TOKEN" if os.environ.get("GITHUB_TOKEN") else "GITHUB_PAT"
        token = try_token(env_token, f"environment variable '{var_name}'")
        if token:
            return token

    # 2. Local config / global config
    try:
        env = _load_env()
        config_token = env.get("GITHUB_TOKEN") or env.get("GITHUB_PAT")
        if config_token:
            from gitea_skills.core import _get_agentic_dir
            local_path = _get_agentic_dir() / "tokens.env"
            global_path = Path.home() / ".gitea_skills.env"
            
            source_desc = "config files"
            def file_has_token(path):
                if path.exists():
                    for line in path.read_text().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() in ("GITHUB_TOKEN", "GITHUB_PAT") and v.strip():
                                return True
                return False
            
            if file_has_token(local_path):
                source_desc = "local config '.agentic_dev/tokens.env'"
            elif file_has_token(global_path):
                source_desc = "global config '~/.gitea_skills.env'"
                
            token = try_token(config_token, source_desc)
            if token:
                return token
    except Exception:
        pass

    # 3. macOS Keychain fallback
    service = get_service_name()
    keychain_token = check_keychain()
    if keychain_token:
        def delete_keychain_token():
            if platform.system() == "Darwin":
                is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
                if is_interactive:
                    try:
                        choice = input(f"Do you want to delete this invalid token from macOS Keychain (service: {service})? [y/N]: ").strip().lower()
                        if choice in ('y', 'yes'):
                            # Try deleting scoped
                            try:
                                subprocess.run(
                                    ["security", "delete-generic-password", "-s", service, "-a", ACCOUNT],
                                    check=True, capture_output=True
                                )
                            except Exception:
                                pass
                            # Try deleting legacy global
                            if service != "friendly-davinci-github":
                                try:
                                    subprocess.run(
                                        ["security", "delete-generic-password", "-s", "friendly-davinci-github", "-a", ACCOUNT],
                                        check=True, capture_output=True
                                    )
                                except Exception:
                                    pass
                            print("Invalid token deleted from macOS Keychain.", file=sys.stderr)
                    except Exception as ke:
                        print(f"Failed to delete token from macOS Keychain: {ke}", file=sys.stderr)
                else:
                    print(f"[Info] To remove this stale token from your macOS Keychain, run:", file=sys.stderr)
                    print(f"  security delete-generic-password -s {service} -a {ACCOUNT}", file=sys.stderr)

        token = try_token(keychain_token, f"macOS Keychain (service: {service})", delete_on_fail=delete_keychain_token)
        if token:
            return token

    return None

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
    token = get_github_token()
    if token:
        print("Credentials loaded successfully.", file=sys.stderr)
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
