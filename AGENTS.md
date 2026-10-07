# AI Course Builder

This repository turns a topic into a complete online course: curriculum, learning objectives, classes, Marp slides, notes, narration transcripts, quizzes, a static player, and a ZIP bundle.

## Codex routing

- For requests to create, regenerate, or revise a complete course, use the repo-local `course-builder` skill in `.agents/skills/course-builder/SKILL.md`.
- `.claude/agents/*.md` are canonical role specifications. Read the relevant role file before performing that role, ignoring Claude-only frontmatter such as `model` and `tools`.
- `.claude/skills/*/SKILL.md` are canonical domain instructions. Read the skill paired with the current role instead of duplicating its rules.
- Do not rename, move, or remove `.claude/`; existing scripts contain paths into it.

## State and outputs

- `_workspace/` holds shared planning state, the immutable LO registry, QA reports, and build logs.
- `course/` holds generated course assets and the final static site.
- Preserve file names, JSON schemas, LO ids, partial-rerun semantics, and the coherence gate.
- For Codex-created courses, default to `language="ru"` unless the user explicitly requests another supported language (`ru`, `ko`, or `en`).

## Build and validation

- Build without TTS: `SKIP_TTS=1 bash .claude/skills/asset-build/scripts/build-bundle.sh course`
- Force TTS rebuild: `FORCE_TTS=1 bash .claude/skills/asset-build/scripts/build-bundle.sh course`
- Validate shell: `bash -n .claude/skills/asset-build/scripts/build-bundle.sh`
- Validate Python: `python -m py_compile scripts/*.py`
- Validate changes: `git diff --check`

On Windows, run shell commands with Git Bash. The build scripts select a working Python interpreter and fall back to Python's standard library when `jq` or `zip` is unavailable.

