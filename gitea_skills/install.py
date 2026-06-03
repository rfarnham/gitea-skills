#!/usr/bin/env python3
"""Installer for the gitea-skills agentic development loop.

Usage:
    python -m gitea_skills.install --target-dir /path/to/project
"""

import os
import sys
from pathlib import Path


TOKENS_TEMPLATE = """# Gitea Skills — Token Configuration
# Fill in the values below after running scripts/setup.sh in a project
# that has the Gitea Docker environment.

GITEA_URL=http://localhost:3000
REPO_OWNER=admin
REPO_NAME=<your-repo-name>

# Agent tokens (created by setup.sh)
DEVELOPER_AGENT_TOKEN=
REVIEWER_AGENT_TOKEN=
ADMIN_TOKEN=
"""

CONFIG_TEMPLATE = """# Gitea Skills — Project Configuration
TEST_COMMAND=pytest
"""


def run_install(target_dir: str = "."):
    target = Path(target_dir).resolve()
    agentic_dir = target / ".agentic_dev"
    
    print(f"Setting up gitea-skills in: {target}")
    
    # 1. Create .agentic_dev directory and templates
    agentic_dir.mkdir(parents=True, exist_ok=True)
    
    tokens_path = Path.home() / ".gitea_skills.env"
    if not tokens_path.exists():
        tokens_path.write_text(TOKENS_TEMPLATE)
        print(f"  Created: {tokens_path} (Global configuration)")
    else:
        print(f"  Exists:  {tokens_path} (Global configuration skipped)")
    
    config_path = agentic_dir / "config.env"
    if not config_path.exists():
        config_path.write_text(CONFIG_TEMPLATE)
        print(f"  Created: {config_path}")
    else:
        print(f"  Exists:  {config_path} (skipped)")
    
    # 2. Ensure .agentic_dev is in .gitignore
    gitignore = target / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".agentic_dev/" not in content:
            with open(gitignore, "a") as f:
                f.write("\n# Gitea agentic dev loop state\n.agentic_dev/\n")
            print(f"  Updated: {gitignore}")
    else:
        gitignore.write_text("# Gitea agentic dev loop state\n.agentic_dev/\n")
        print(f"  Created: {gitignore}")
    
    # 3. Create plugin symlink in ~/.gemini/config/plugins/
    plugin_dir = Path.home() / ".gemini" / "config" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    import gitea_skills
    package_dir = Path(gitea_skills.__file__).parent
    symlink_path = plugin_dir / "gitea-skills"
    
    if symlink_path.is_symlink() or symlink_path.exists():
        print(f"  Exists:  {symlink_path} (skipped)")
    else:
        symlink_path.symlink_to(package_dir)
        print(f"  Symlink: {symlink_path} -> {package_dir}")
    
    print("")
    print("Setup complete! Next steps:")
    print(f"  1. Edit {tokens_path} with your Gitea tokens (if not already done)")
    print(f"  2. Edit {config_path} with your test command")
    print("  3. The gitea-skills plugin is now globally available to Antigravity agents")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Install gitea-skills for a project")
    parser.add_argument("--target-dir", default=".", help="Target project directory")
    args = parser.parse_args()
    run_install(args.target_dir)


if __name__ == "__main__":
    main()
