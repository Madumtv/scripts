---
name: finishing-a-development-branch
description: Use when a feature or bugfix is approved and ready to be merged into the main branch.
---

# Finishing a Development Branch

## Overview
Safely merge approved changes from a development branch back into the main line of development, ensuring no regression.

## Process
1. **Verify Approval:** Confirm the code review was successful.
2. **Sync Main:** `git checkout main` and `git pull origin main`.
3. **Merge/Rebase:** Perform the merge or rebase of the feature branch.
4. **Final Tests:** Run the full test suite one last time on the merged result.
5. **Cleanup:** Delete the local and remote feature branch if the merge was successful.

## Decision Points
- Use **Squash and Merge** if the Git history of the branch is messy.
- Use **Standard Merge** to preserve individual commits for complex histories.
