#!/usr/bin/env python3
"""Deduplication engine for Gitea issues."""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Add parent directory to sys.path to allow importing when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gitea_skills import gitea_api
from gitea_skills.core import _load_env

def run_dedup() -> str:
    """Analyze open issues and suggest duplicates."""
    try:
        env = _load_env()
    except Exception as e:
        return f"Error loading environment: {e}"

    token = env.get("DEVELOPER_AGENT_TOKEN") or env.get("ADMIN_TOKEN") or env.get("REVIEWER_AGENT_TOKEN", "")
    owner = env.get("REPO_OWNER", "admin")
    repo = env.get("REPO_NAME", "friendly-davinci")
    gitea_api.GITEA_URL = env.get("GITEA_URL", "http://localhost:3000")

    try:
        issues = gitea_api.list_issues(token, owner, repo, state="open", type="issues")
    except Exception as e:
        return f"Error listing issues from Gitea: {e}"

    if not issues or len(issues) < 2:
        return f"Analyzing {len(issues) if issues else 0} open issues... Not enough issues to compare."

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return _dedup_llm(issues, api_key)
    else:
        return _dedup_heuristic(issues)

def _dedup_llm(issues: list, api_key: str) -> str:
    """Compare issues using the Gemini REST API."""
    prompt_issues = []
    for issue in issues:
        idx = issue.get("number")
        title = issue.get("title")
        body = issue.get("body") or ""
        prompt_issues.append(f"Issue #{idx}: {title}\nDescription: {body}\n---")

    issues_str = "\n".join(prompt_issues)

    prompt = f"""You are an AI assistant analyzing issue reports for a software repository.
Compare the following list of open issues and identify any duplicates.
List of issues:
{issues_str}

For each group of duplicate issues, identify which is the primary issue and which are duplicates.
Format your response as a JSON array of objects:
[
  {{"duplicate_index": 2, "primary_index": 1, "reason": "Both issues describe division by zero crash in the calculator."}}
]
Return ONLY this JSON array, and nothing else. If there are no duplicates, return an empty array []."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean potential markdown block formatting from JSON response
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```json"):
                    text = "\n".join(lines[1:-1])
                elif lines[0].startswith("```"):
                    text = "\n".join(lines[1:-1])

            dups = json.loads(text.strip())
            return _format_dup_results(dups, "Gemini LLM semantic analysis")
    except Exception as e:
        # Fallback to heuristic if LLM call fails
        print(f"Warning: Gemini API call failed ({e}). Falling back to heuristic comparison.", file=sys.stderr)
        return _dedup_heuristic(issues)

def _dedup_heuristic(issues: list) -> str:
    """Compare issues using token Jaccard similarity heuristics."""
    dups = []
    
    def get_words(text):
        if not text:
            return set()
        # Clean punctuation and split
        cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
        return set(cleaned.split())

    # Pairwise comparison
    for i in range(len(issues)):
        for j in range(i + 1, len(issues)):
            issue1 = issues[i]
            issue2 = issues[j]
            
            words1 = get_words(issue1.get("title", "") + " " + (issue1.get("body", "") or ""))
            words2 = get_words(issue2.get("title", "") + " " + (issue2.get("body", "") or ""))
            
            if not words1 or not words2:
                continue
                
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            similarity = len(intersection) / len(union)
            
            if similarity >= 0.35:
                # Older issue is primary (lower index)
                idx1 = issue1.get("number")
                idx2 = issue2.get("number")
                primary = min(idx1, idx2)
                duplicate = max(idx1, idx2)
                dups.append({
                    "duplicate_index": duplicate,
                    "primary_index": primary,
                    "reason": f"Text token Jaccard similarity score: {similarity:.2f} (threshold is 0.35)"
                })
                
    return _format_dup_results(dups, "Text similarity heuristics")

def _format_dup_results(dups: list, method_name: str) -> str:
    if not dups:
        return f"Analyzing open issues via {method_name}... No duplicates identified."
        
    lines = [f"Analyzing open issues via {method_name}... Found potential duplicates:"]
    for d in dups:
        dup_idx = d.get("duplicate_index")
        prim_idx = d.get("primary_index")
        reason = d.get("reason")
        lines.append(f"\n[Recommendation] Issue #{dup_idx} is a duplicate of Issue #{prim_idx}.")
        lines.append(f"  Reason: {reason}")
        lines.append(f"  To close the duplicate:")
        lines.append(f"    gitea-skills issue close {dup_idx}")
    return "\n".join(lines)

if __name__ == "__main__":
    print(run_dedup())
