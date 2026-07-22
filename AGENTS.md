# Repository Agent Instructions

## Project purpose

- This repository is a learning and portfolio project for LangChain 1.2, LangGraph, DeepSeek, tool calling, memory, RAG, and Agent engineering.
- Keep examples understandable for a learner with basic Python experience.
- When handing work back, explain the main design, execution flow, and interview-ready talking points in Chinese.

## Implementation workflow

1. Inspect the relevant code and `git status` before editing.
2. Preserve user-authored and unrelated changes.
3. Keep each change focused on one coherent feature or fix.
4. Never hard-code API keys, passwords, tokens, or other secrets.
5. Do not read, print, stage, or commit `.env`.
6. Prefer safe, bounded tools over arbitrary file access or arbitrary code execution.
7. Update README or learning documentation when behavior or usage changes.

## Verification

- Use the existing Conda interpreter:

  ```powershell
  & "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m unittest discover -s tests -v
  ```

- Run the most relevant tests after code changes and report the actual result.
- Do not make paid or external DeepSeek API calls unless the user requests or approves the call.
- Before sending project content to an external model or service, state what will be transmitted and obtain any required approval.

## Git workflow

After completing a coherent, working milestone:

1. Run relevant tests.
2. Inspect `git diff` and `git status`.
3. Confirm that `.env`, secrets, `.idea`, `.tools`, caches, generated artifacts, and unrelated files are not staged.
4. Stage only files related to the current task.
5. Create a concise Conventional Commit, for example:
   - `feat: add persistent conversation memory`
   - `fix: prevent project path traversal`
   - `test: cover agent tool failures`
   - `docs: explain agent execution flow`
6. Push the current branch to the configured `origin` after the current publication scope is authorized.
7. Report the commit hash and push result.

## Git safety

- Do not add the unrelated root `main.py` unless the user explicitly asks for it.
- Never run force-push, destructive reset, history rewrite, remote-branch deletion, or tag deletion without explicit user approval.
- If tests fail, the remote is missing, authentication is required, sensitive data is detected, or pushing is blocked, stop and explain the exact next action.
- Do not use GitHub web uploads as a substitute for `git push` when that would create unrelated history or flatten project directories.
