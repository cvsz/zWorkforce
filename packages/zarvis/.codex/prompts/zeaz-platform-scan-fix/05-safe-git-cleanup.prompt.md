# Safe Git Cleanup

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

Goal:
Clean the working tree without losing useful local work.

Rules:
- Do not use git clean -fdx.
- Do not use git reset --hard.
- Do not delete untracked files without backing them up.
- Do not stage generated logs.
- Do not stage secrets.

Steps:
1. Print:
   git status -sb
   git diff --name-only
   git diff --name-only --cached
   git diff --name-only --diff-filter=U

2. If unmerged files exist:
   - stop and report them.
   - do not continue.

3. Backup untracked build logs:
   - reports/platform/build-logs
   - *.log
   - coverage
   - .next
   - dist
   - build

4. Move generated logs to:
   /home/zeazdev/zeaz-local-backups/<timestamp>/

5. Update .gitignore only for safe generated paths, if missing.

6. Confirm:
   git status -sb

7. Output exact safe next command.
