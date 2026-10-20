---
name: git-work-tracking
description: "User wants Claude to keep track of all git work (commits, pushes, branches) in the HRI-class-materials repo"
metadata:
  node_type: memory
  type: project
  originSessionId: d398784a-7ee6-478b-94d4-ea64dba28229
  modified: 2026-10-20T03:32:26.406Z
---

User asked (2026-10-19) that Claude keep track of all git work for this repo (`RaiYan163/HRI-class-materials`, branch `main`).

**Why:** The repo is class material for an HRI course; the user wants a clear record of what changes were made and when.

**How to apply:** At the start of a session, run `git status` and `git log` to see what changed since the last entry below. After any commit, push, branch or merge I perform, append a dated line to the log below and tell the user. Never commit or push without being asked.

## Log
- 2026-10-19: Baseline. One commit (`1a7dde9 Initial commit`), `main` in sync with `origin/main`. Untracked: `.DS_Store`, `intro_claude_code/` (contains `HRI_claudeUse_demo_previous`, `HRI_claude_code.pptx`, `experiment`).
