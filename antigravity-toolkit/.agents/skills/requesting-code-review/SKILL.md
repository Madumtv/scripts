---
name: requesting-code-review
description: Use when you've completed a feature or bugfix and want to push to GitHub for review via a Pull Request.
---

# Requesting Code Review

## Overview
Automate the process of pushing changes to a remote repository and initiating the formal review process (Pull Request).

## Process
1. **Prepare branch:** Ensure all code is committed and tests pass.
2. **Push to GitHub:** Use `git push origin [branch-name]`.
3. **Create Pull Request:** 
   - Use GitHub CLI (`gh pr create`) if available.
   - Otherwise, provide the user with the direct GitHub URL to create the PR.
4. **Link to Plan:** Ensure the PR description references the original implementation plan or issue.

## Verification
- [ ] Code is on the remote branch.
- [ ] PR is created or URL provided to the user.
- [ ] CI/CD (if any) is triggered.
