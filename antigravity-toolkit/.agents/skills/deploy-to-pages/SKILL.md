---
name: deploy-to-pages
description: Use when a static site is ready to be hosted on GitHub Pages.
---

# Deploy to GitHub Pages

## Overview
Automate the deployment of the current project to the `gh-pages` branch to make it accessible via a public URL.

## Process
1. **Prepare branch:** `git checkout -b gh-pages` (or switch to it if exists).
2. **Sync files:** Ensure only production files (HTML/CSS/JS) are present if necessary.
3. **Push to Remote:** `git push origin gh-pages --force`.
4. **Switch back:** `git checkout master`.

## Verification
- [ ] URL `https://[username].github.io/[repo-name]/` is live.
- [ ] GitHub Pages settings are set to 'gh-pages branch' (check via Browser Subagent).
