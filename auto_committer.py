#!/usr/bin/env python3
"""
Auto-Committer Utility
----------------------
Generates automated, random Git commits to populate your GitHub contribution graph.
Supports generating multiple commits distributed over past days (backdating).
"""

import os
import sys
import argparse
import subprocess
import datetime
import random

# Fun random commit messages to make the contributions look organic
COMMIT_MESSAGES = [
    "Refactor activity logging module",
    "Update dependency configurations",
    "Optimize internal caching mechanism",
    "Fix minor formatting and syntax issues",
    "Update readme documentation with setup steps",
    "Clean up unused variables and imports",
    "Improve test coverage for utility helpers",
    "Adjust configuration parameters in YAML",
    "Add new helper function for date formatting",
    "Update system configuration settings",
    "Optimize code formatting and comments",
    "Enhance parameter validation checks",
    "Update project dependencies to latest versions",
    "Improve logging formatting for debugging",
    "Minor UI tweak and alignment fixes"
]

ACTIVITY_FILE = "github_activity.txt"

def run_cmd(cmd, env=None):
    """Runs a shell command and returns output, or None on failure."""
    try:
        # Merge environment variables if provided
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=run_env)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\033[91mError running command {' '.join(cmd)}:\033[0m\n{e.stderr.strip()}", file=sys.stderr)
        return None

def check_git():
    """Checks if git is installed and repository is initialized."""
    if not os.path.exists(".git"):
        print("\033[91mError: This directory is not a Git repository. Run 'git init' first.\033[0m")
        sys.exit(1)
    
    version = run_cmd(["git", "--version"])
    if not version:
        print("\033[91mError: Git is not installed or not in PATH.\033[0m")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Generate automated commits to increase GitHub activity.")
    parser.add_argument("-c", "--count", type=int, default=1, help="Number of commits to generate (default: 1)")
    parser.add_argument("-d", "--days", type=int, default=0, help="Distribute commits over the last N days (default: 0, which is today only)")
    parser.add_argument("-p", "--push", action="store_true", help="Push changes to remote origin after generating commits")
    
    args = parser.parse_args()
    
    check_git()
    
    if args.count <= 0:
        print("\033[91mError: Commit count must be at least 1.\033[0m")
        sys.exit(1)
        
    if args.days < 0:
        print("\033[91mError: Days must be 0 or positive.\033[0m")
        sys.exit(1)

    print(f"\033[94mStarting auto-committer: Generating {args.count} commits over the last {args.days} days...\033[0m")
    
    # Calculate commit times
    base_time = datetime.datetime.now()
    
    commits_created = 0
    
    for i in range(args.count):
        # Determine the target date for this commit
        if args.days == 0:
            commit_time = base_time - datetime.timedelta(minutes=random.randint(5, 120) * (i + 1))
        else:
            # Randomly distribute across the N days
            random_day = random.randint(0, args.days)
            # Add random hour and minute
            commit_time = base_time - datetime.timedelta(days=random_day, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
        # Format dates for Git
        # ISO format: 2026-05-25T14:48:39
        git_date_str = commit_time.isoformat()
        
        # Append an entry to the activity log file
        log_entry = f"[{git_date_str}] Generated commit #{i+1} of {args.count} - ID: {random.getrandbits(32):08x}\n"
        with open(ACTIVITY_FILE, "a") as f:
            f.write(log_entry)
            
        # Add file to Git staging
        if run_cmd(["git", "add", ACTIVITY_FILE]) is None:
            print("\033[91mFailed to stage changes.\033[0m")
            sys.exit(1)
            
        # Commit with backdated env variables
        msg = random.choice(COMMIT_MESSAGES)
        commit_env = {
            "GIT_AUTHOR_DATE": git_date_str,
            "GIT_COMMITTER_DATE": git_date_str
        }
        
        commit_res = run_cmd(["git", "commit", "-m", f"{msg} (Automated update)"], env=commit_env)
        if commit_res is not None:
            print(f"\033[92m[Success]\033[0m Committed: '{msg}' on {commit_time.strftime('%Y-%m-%d %H:%M:%S')}")
            commits_created += 1
        else:
            print("\033[91mFailed to commit changes.\033[0m")
            sys.exit(1)
            
    print(f"\033[92mSuccessfully created {commits_created} commits.\033[0m")
    
    if args.push:
        print("\033[94mPushing commits to remote repository...\033[0m")
        push_res = run_cmd(["git", "push", "origin", "main"])
        if push_res is not None:
            print("\033[92mSuccessfully pushed changes to remote repository!\033[0m")
        else:
            print("\033[91mFailed to push changes to remote repository.\033[0m")

if __name__ == "__main__":
    main()
