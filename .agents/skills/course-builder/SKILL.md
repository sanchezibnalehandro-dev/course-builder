---
name: course-builder
description: Создаёт, пересобирает и точечно обновляет полный онлайн-курс со структурой, LO, слайдами, конспектами, транскриптами, тестами, QA и HTML-плеером. Использовать для запросов «создай курс», «сделай учебную программу», «курс со слайдами и тестами» и для partial rerun; не использовать для одного отдельного артефакта.
---

# Course Builder для Codex

Оркестрируй существующий пятифазный pipeline, не создавая параллельный framework. `.claude/agents/` содержит спецификации ролей, `.claude/skills/` — канонические предметные правила, `_workspace/` — общее состояние, `course/` — итоговые материалы.

## 0. Определи режим и параметры

Перед работой проверь существующие `_workspace/` и `course/`.

- Нет `_workspace/`: новый запуск с Phase 1.
- Есть `_workspace/`, пользователь дал новую тему или попросил полный перезапуск: перенеси прежнее состояние в следующий свободный `_workspace_prev<N>/`, затем начни с Phase 1.
- Пользователь указал scope: partial rerun без переноса `_workspace/`.
- Намерение неясно при существующем состоянии: уточни, продолжать, пересобрать всё или изменить scope.

Параметры:

- `topic` обязателен.
- Codex defaults: `audience="intermediate developers"`, `depth="standard"`, `target_duration_min=120`, `language="ru"`, `tone="friendly"`, `hitl=true`.
- Поддерживаемые языки: `ru`, `ko`, `en`. Явное указание пользователя всегда важнее default. После записи Course Spec не меняй язык посреди запуска.
- `hitl=false`, если пользователь просит выполнить всё автоматически.

Scope tokens: `S<n>`, `S<n>.C<m>`, `S<n>.C<m>.tone=X`, `S<n>.quiz`; несколько scope разделяются запятой.

Partial rerun обязан:

1. Сохранять существующие LO id; вне scope LO остаются byte-for-byte без изменений.
2. Не трогать class assets и audio вне scope.
3. При quiz rerun сохранять ids неизменённых items.
4. Запускать coherence regression только для scope и его зависимостей.

## Как выполнять роли

Перед каждой ролью полностью прочитай соответствующие два источника:

| Role | Role specification | Domain skill |
|---|---|---|
| curriculum architect | `.claude/agents/curriculum-architect.md` | `.claude/skills/curriculum-design/SKILL.md` |
| section designer | `.claude/agents/section-designer.md` | `.claude/skills/curriculum-design/SKILL.md` |
| class planner | `.claude/agents/class-planner.md` | `.claude/skills/class-planning/SKILL.md` |
| slide author | `.claude/agents/slide-author.md` | `.claude/skills/slide-authoring/SKILL.md` |
| note writer | `.claude/agents/note-writer.md` | `.claude/skills/note-writing/SKILL.md` |
| script writer | `.claude/agents/script-writer.md` | `.claude/skills/script-writing/SKILL.md` |
| quiz master | `.claude/agents/quiz-master.md` | `.claude/skills/quiz-generation/SKILL.md` |
| coherence reviewer | `.claude/agents/coherence-reviewer.md` | `.claude/skills/coherence-review/SKILL.md` |
| asset builder | `.claude/agents/asset-builder.md` | `.claude/skills/asset-build/SKILL.md` |
| TTS synthesizer | `.claude/agents/tts-synthesizer.md` | `.claude/skills/tts-synthesis/SKILL.md` |

Игнорируй Claude-specific frontmatter и вызовы `TeamCreate`, `TeamDelete`, `TaskCreate`, `TaskUpdate`, `Agent(...)`, `SendMessage`, а также фиксированный `model="opus"`. Это описание старого harness, не исполняемый API Codex.

Если среда предоставляет native delegation, отдавай независимые section/class задачи отдельным исполнителям и передавай им пути к role/domain instructions. Если delegation недоступна, выполняй те же роли последовательно в главном агенте. Никогда не жертвуй контрактами ради буквального воспроизведения multi-agent механики.

## Пять фаз

### 1. Design

1. Curriculum architect создаёт:
   - `_workspace/01_architect_course_spec.json`
   - `_workspace/01_architect_learning_objectives.json`
2. Section designer создаёт `_workspace/02_section_<sid>.json` для каждой секции; независимые секции можно выполнять параллельно.
3. Class planner создаёт `_workspace/03_class_<cid>_beats.json`; соблюдай `depends_on` и топологический порядок.

LO registry — единый источник истины. Никогда не перенумеровывай выданные LO id.

### 2. Content

Для каждого class:

1. Создай `slide.source.md` и `note.md` независимо.
2. После готовности слайдов создай `transcript.txt`, потому что transcript ссылается на номера слайдов.

При `hitl=true` после первого class покажи пользователю короткие фрагменты трёх артефактов и дождись `yes`, `edit: ...` или `regen`.

### 3. Assessment

Quiz master создаёт `course/sections/<section>/quiz.json` после готовности всех classes секции. Независимые секции можно выполнять параллельно.

### 4. QA

Coherence reviewer проверяет структуру, LO coverage, Bloom balance, slide↔transcript cues, note↔slide references, tone, quiz factuality и speakability. Запиши оба файла:

- `_workspace/99_coherence_report.json`
- `_workspace/99_coherence_report.md`

При `revise` направь issue ответственному автору, обнови только нужные артефакты и повтори проверку. Максимум две итерации на issue; затем остановись и запроси решение пользователя. Build разрешён только при JSON `overall: "pass"`.

### 5. Build

Запусти существующий pipeline:

```bash
SKIP_TTS=1 bash .claude/skills/asset-build/scripts/build-bundle.sh course
```

Не устанавливай `SKIP_TTS=1`, если пользователь запросил TTS и среда действительно настроена. Ожидаемые финальные файлы:

- `course/manifest.json`
- `course/index.html`
- `course/build/bundle.zip`

`SKIP_PLAYER=1` пропускает генерацию player HTML, но текущий build всё равно рендерит PNG.

## HITL

При `hitl=true` сделай три checkpoint: после Course Spec, после первого class и после coherence report. Покажи человекочитаемое резюме и предложи `yes`, `edit: ...`, `regen`. Записывай ответы append-only в `_workspace/97_hitl_log.md`. Не продолжай без ответа. При `hitl=false` не останавливайся, но кратко сообщай завершение фаз.

## Ошибки и завершение

- Роль можно повторить один раз; после повторного сбоя запиши `_workspace/98_failures.md` и передай проблему в QA.
- Не удаляй противоречащие источники: зафиксируй обе версии.
- Не обходи coherence gate и не заявляй TTS проверенным без реального API-вызова.
- В финале сообщи режим запуска, созданные артефакты, coherence verdict, build result и реальные ограничения.

