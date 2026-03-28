---
name: using-git-worktrees
description: Use when managing multiple tasks or branches in parallel to maintain isolated environments.
---

# Using Git Worktrees

## Overview
Leverage `git worktree` to work on multiple branches simultaneously in separate directories without switching context in a single folder.

## Benefits
- No `git stash` needed when switching tasks.
- Run tests on one branch while coding on another.
- Maintain clean environment for each feature.

## Common Operations
- **Add worktree:** `git worktree add ../[folder-name] [branch-name]`
- **List worktrees:** `git worktree list`
- **Remove worktree:** `git worktree remove ../[folder-name]`

## When to use
- Parallel development of two features.
- Quick bugfix while middle of a long-running feature.
- Comparing behavior between different branches.
