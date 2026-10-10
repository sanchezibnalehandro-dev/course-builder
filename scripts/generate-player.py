#!/usr/bin/env python3
"""
Generate a self-contained HTML player for the course.

Produces:
  course/index.html                                    — course home, TOC
  course/sections/<sec>/quiz.html                      — interactive quiz per section
  course/sections/<sec>/classes/<cls>/player.html      — slide+audio+transcript player

Inputs: course/manifest.json + per-class assets (slides_png/, audio/, transcript.txt).
Idempotent — overwrites existing player/quiz/index HTML.
"""
import argparse
import html
import json
import re
import subprocess
from pathlib import Path

SLIDE_RE = re.compile(r'^\s*\[slide\s+(\d+)\]\s*$')
PAUSE_RE = re.compile(r'\[pause:(\d+)\]')


# ── i18n strings for player chrome (slide-deck UI) ──────────────────────────
# Scope: player.html only. quiz.html chrome and course index.html landing
# remain in Korean; their i18n is follow-up work.
_PLAYER_STRINGS = {
    "ko": {
        "menu_title": "목차 열기/닫기",
        "home": "홈",
        "class_label": "수업",
        "slide_label": "슬라이드",
        "slide_unit": "장",
        "min_unit": "분",
        "speed_title": "재생 속도",
        "prev": "이전",
        "play": "재생",
        "pause": "일시정지",
        "next": "다음",
        "transcript_h2": "발화 스크립트",
        "end_title": "수업을 완료했어요!",
        "end_sub": "다음으로 이동하거나 배운 내용을 점검해보세요.",
        "resume_prefix": "이전 위치",
        "resume_yes": "이어 듣기",
        "resume_no": "처음부터",
        "quiz_cta_footer": "섹션 퀴즈 풀기",
        "back_to_toc": "목차로",
        "cta_this_section": "이 섹션",
        "cta_final_quiz": "마지막 퀴즈 풀기",
        "cta_done": "완료",
        "cta_course_toc": "코스 목차로",
        "cta_check_section": "이 섹션 점검",
        "cta_section_quiz": "섹션 퀴즈 풀기",
        "cta_next_section": "다음 섹션",
        "cta_next_class": "다음 수업",
        "cta_check_first": "먼저 점검",
        "cta_section_quiz_short": "섹션 퀴즈",
        "cta_continue": "계속 학습",
        "toc_quiz_tpl": "섹션 퀴즈 ({n}문항)",
        # quiz.html chrome
        "quiz_title": "퀴즈",
        "back_toc_short": "목차",
        "items_unit": "문항",
        "submit_grade": "제출하고 채점하기",
        "score_correct": "맞혔습니다",
        "short_answer_note_prefix": "(서술형 ",
        "short_answer_note_mid": "문항은 rubric 자가채점",
        "next_label": "다음",
        "true_label": "참 (True)",
        "false_label": "거짓 (False)",
        "answer_placeholder": "답변을 입력하세요...",
        "rubric_heading": "채점 기준",
        "distractor_heading": "오답 해설",
        "correct_label": "정답",
        # index.html landing
        "landing_stats_tpl": "총 {n_cls}개 class · {n_lo}개 학습 목표 · {mins:.1f}분",
        "landing_class_stats_tpl": "{n_slides}장 · {dur:.1f}분 · LO {los}",
    },
    "en": {
        "menu_title": "Toggle TOC",
        "home": "Home",
        "class_label": "Class",
        "slide_label": "Slide",
        "slide_unit": " slides",
        "min_unit": " min",
        "speed_title": "Playback speed",
        "prev": "Prev",
        "play": "Play",
        "pause": "Pause",
        "next": "Next",
        "transcript_h2": "Transcript",
        "end_title": "You finished the class!",
        "end_sub": "Move on to the next step, or review what you just learned.",
        "resume_prefix": "Previous position",
        "resume_yes": "Resume",
        "resume_no": "Start over",
        "quiz_cta_footer": "Take section quiz",
        "back_to_toc": "Back to TOC",
        "cta_this_section": "This section",
        "cta_final_quiz": "Take the final quiz",
        "cta_done": "Done",
        "cta_course_toc": "Back to course TOC",
        "cta_check_section": "Review this section",
        "cta_section_quiz": "Take section quiz",
        "cta_next_section": "Next section",
        "cta_next_class": "Next class",
        "cta_check_first": "Check first",
        "cta_section_quiz_short": "Section quiz",
        "cta_continue": "Continue",
        "toc_quiz_tpl": "Section quiz ({n} items)",
        # quiz.html chrome
        "quiz_title": "Quiz",
        "back_toc_short": "TOC",
        "items_unit": "items",
        "submit_grade": "Submit & grade",
        "score_correct": "correct",
        "short_answer_note_prefix": "(",
        "short_answer_note_mid": " short-answer items rely on rubric self-grading",
        "next_label": "Next",
        "true_label": "True",
        "false_label": "False",
        "answer_placeholder": "Type your answer...",
        "rubric_heading": "Rubric",
        "distractor_heading": "Why the other choices are wrong",
        "correct_label": "Correct answer",
        # index.html landing
        "landing_stats_tpl": "{n_cls} classes · {n_lo} LOs · {mins:.1f} min",
        "landing_class_stats_tpl": "{n_slides} slides · {dur:.1f} min · LO {los}",
    },
    "ru": {
        "menu_title": "Открыть или закрыть содержание",
        "home": "Главная",
        "class_label": "Урок",
        "slide_label": "Слайд",
        "slide_unit": " слайдов",
        "min_unit": " мин",
        "speed_title": "Скорость воспроизведения",
        "prev": "Назад",
        "play": "Воспроизвести",
        "pause": "Пауза",
        "next": "Далее",
        "transcript_h2": "Текст лекции",
        "end_title": "Занятие завершено!",
        "end_sub": "Переходите дальше или проверьте, что запомнили.",
        "resume_prefix": "Предыдущее место",
        "resume_yes": "Продолжить",
        "resume_no": "Сначала",
        "quiz_cta_footer": "Пройти тест раздела",
        "back_to_toc": "К содержанию",
        "cta_this_section": "Этот раздел",
        "cta_final_quiz": "Пройти итоговый тест",
        "cta_done": "Готово",
        "cta_course_toc": "К содержанию курса",
        "cta_check_section": "Проверить этот раздел",
        "cta_section_quiz": "Пройти тест раздела",
        "cta_next_section": "Следующий раздел",
        "cta_next_class": "Следующее занятие",
        "cta_check_first": "Сначала проверка",
        "cta_section_quiz_short": "Тест раздела",
        "cta_continue": "Продолжить обучение",
        "toc_quiz_tpl": "Тест раздела ({n} вопросов)",
        "quiz_title": "Тест",
        "back_toc_short": "Содержание",
        "items_unit": "вопросов",
        "submit_grade": "Отправить и проверить",
        "score_correct": "правильных ответов",
        "short_answer_note_prefix": "(",
        "short_answer_note_mid": " открытых вопросов проверяются самостоятельно по критериям",
        "next_label": "Далее",
        "true_label": "Верно",
        "false_label": "Неверно",
        "answer_placeholder": "Введите ответ...",
        "rubric_heading": "Критерии оценки",
        "distractor_heading": "Почему другие варианты неверны",
        "correct_label": "Правильный ответ",
        "landing_stats_tpl": "{n_cls} занятий · {n_lo} целей обучения · {mins:.1f} мин",
        "landing_class_stats_tpl": "{n_slides} слайдов · {dur:.1f} мин · LO {los}",
        "ai_voice_notice": "Голос озвучки сгенерирован искусственным интеллектом.",
    },
}

# Keep the disclosure key available for legacy locales without changing their UI.
_PLAYER_STRINGS["ko"].setdefault("ai_voice_notice", "AI로 생성된 음성입니다.")
_PLAYER_STRINGS["en"].setdefault("ai_voice_notice", "The narration voice is AI-generated.")


def _tx(lang: str) -> dict:
    return _PLAYER_STRINGS.get(lang, _PLAYER_STRINGS["ko"])


def parse_transcript_by_slide(text: str) -> dict:
    """Return {slide_no: [line, ...]} with [pause:N] stripped."""
    out = {}
    current = None
    for line in text.splitlines():
        m = SLIDE_RE.match(line)
        if m:
            current = int(m.group(1))
            out[current] = []
            continue
        if current is None:
            continue
        cleaned = PAUSE_RE.sub("", line).strip()
        if cleaned:
            out[current].append(cleaned)
    return out


def char_proportional_line_times(lines: list[str], total_sec: float) -> list[dict]:
    """Approximate per-line start/end by weighting lines by character count.

    MVP for live-subtitle highlight: no whisper-align, no word-level timing —
    just splits the slide's MP3 duration proportionally to line length. Accuracy
    degrades on lines with skewed speaking density, but works well enough for a
    'which sentence am I on?' affordance.
    """
    if not lines or total_sec <= 0:
        return []
    weights = [max(len(ln), 1) for ln in lines]
    total_w = sum(weights)
    cursor = 0.0
    out = []
    for w in weights:
        frac = w / total_w
        dur = total_sec * frac
        out.append({"start": round(cursor, 3), "end": round(cursor + dur, 3)})
        cursor += dur
    return out


def mp3_duration(path: Path) -> float:
    if not path.exists():
        return 0.0
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


PLAYER_TMPL = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root{{--ink:#17232d;--ink-2:#22313d;--paper:#f5f1e8;--surface:#fffdf8;--line:#d9d2c5;--muted:#6b746f;--signal:#ff5c35;--signal-dark:#d84524;--lime:#b9e34b;--focus:#376fba;--shadow:0 18px 50px rgba(23,35,45,.12)}}
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:"Segoe UI Variable","Segoe UI",Arial,sans-serif;background:var(--paper);color:var(--ink);line-height:1.55;overflow-x:hidden}}
  a{{color:var(--signal-dark);text-decoration-thickness:1px;text-underline-offset:3px}}a:hover{{color:#a93218}}
  button,a{{-webkit-tap-highlight-color:transparent}}
  button:focus-visible,a:focus-visible{{outline:3px solid var(--focus);outline-offset:3px}}
  header{{padding:15px 24px;background:var(--surface);border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:center;flex-wrap:wrap;position:relative}}
  header::after{{content:"";position:absolute;left:0;bottom:-1px;width:118px;height:3px;background:var(--signal)}}
  header h1{{font-size:19px;line-height:1.2;margin:0;font-weight:720;letter-spacing:-.025em;min-width:0;overflow-wrap:anywhere}}
  header .meta{{color:var(--muted);font-size:13px;margin-left:auto}}
  button.menu-toggle{{background:var(--ink);border:1px solid var(--ink);color:#fff;border-radius:10px;padding:7px 11px;font-size:14px;cursor:pointer}}
  button.menu-toggle:hover{{background:var(--ink-2)}}
  #progress{{padding:10px 24px;background:var(--ink);display:flex;gap:14px;align-items:center;font-size:12px;color:#9eaaa6}}
  #progress .bar{{flex:1;height:5px;background:#33424d;border-radius:999px;overflow:hidden}}
  #progress .bar .fill{{height:100%;background:var(--lime);border-radius:999px;transition:width .3s ease}}
  #progress .bar:last-child .fill{{background:var(--signal)}}
  #progress .label{{white-space:nowrap;text-transform:uppercase;letter-spacing:.06em}}
  #progress strong{{color:#fff;font-weight:700}}
  main{{display:grid;grid-template-columns:230px minmax(0,1fr) 340px;gap:18px;padding:22px;width:100%;max-width:1740px;margin:0 auto;align-items:start}}
  main>*{{min-width:0}}
  aside#toc{{background:var(--ink);color:#fff;border-radius:16px;padding:18px 14px;overflow-y:auto;max-height:calc(100vh - 150px);position:sticky;top:18px;box-shadow:var(--shadow)}}
  aside#toc h3{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#9eaaa6;margin:18px 8px 8px;font-weight:650}}
  aside#toc h3:first-child{{margin-top:2px}}
  aside#toc ul{{list-style:none;padding:0;margin:0 0 12px}}
  aside#toc li{{padding:9px 10px;border-radius:10px;margin-bottom:3px;font-size:13px;border:1px solid transparent}}
  aside#toc a{{color:#d9dfdc;text-decoration:none;display:block}}
  aside#toc li:hover{{background:#22313d}}
  aside#toc li.current{{background:#2b3a45;border-color:#41515d;box-shadow:inset 4px 0 0 var(--signal)}}
  aside#toc li.current a{{color:#fff;font-weight:700}}
  aside#toc li.quiz a{{color:var(--lime)}}
  #stage{{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:14px;display:flex;flex-direction:column;gap:11px;min-width:0;box-shadow:var(--shadow)}}
  #slide-wrap{{aspect-ratio:16/9;background:var(--ink);border-radius:12px;overflow:hidden;display:flex;align-items:center;justify-content:center}}
  #slide{{width:100%;height:100%;object-fit:contain;display:block}}
  #controls{{display:flex;gap:8px;align-items:center;padding:7px 2px 2px}}
  button{{background:#fff;color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:9px 14px;font:inherit;font-size:14px;font-weight:650;cursor:pointer;transition:transform .14s ease,background .14s ease,border-color .14s ease}}
  button:hover{{background:#f0eadf;border-color:#bfb6a7;transform:translateY(-1px)}}
  button:disabled{{opacity:.38;cursor:not-allowed;transform:none}}
  button.play{{background:var(--signal);border-color:var(--signal);color:#fff;min-width:116px}}
  button.play:hover{{background:var(--signal-dark);border-color:var(--signal-dark)}}
  button.speed{{min-width:60px;font-variant-numeric:tabular-nums}}
  #pos{{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums;margin-left:auto}}
  audio{{width:100%}}
  .no-audio #play,.no-audio #speed,.no-audio audio{{display:none}}
  .ai-voice-notice{{margin:-3px 2px 0;color:var(--muted);font-size:12px}}
  aside#transcript{{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:20px;max-height:calc(100vh - 174px);overflow-y:auto;min-width:0;box-shadow:var(--shadow)}}
  aside#transcript h2{{margin:0 0 15px;font-size:12px;color:var(--signal-dark);font-weight:750;text-transform:uppercase;letter-spacing:.1em}}
  #tx-body p{{margin:0 0 9px;transition:background .2s,color .2s;border-radius:8px;padding:5px 8px;color:#34434d;overflow-wrap:anywhere}}
  #tx-body p.active{{background:#fff0ea;color:var(--ink);box-shadow:inset 3px 0 0 var(--signal)}}
  #thumbs{{display:flex;gap:10px;padding:14px 22px;overflow-x:auto;border-top:1px solid #2e3d48;background:var(--ink)}}
  .thumb{{flex:0 0 132px;aspect-ratio:16/9;border-radius:8px;overflow:hidden;cursor:pointer;border:2px solid transparent;position:relative;opacity:.68;transition:opacity .15s ease,transform .15s ease}}
  .thumb:hover{{opacity:1;transform:translateY(-2px)}}
  .thumb.current{{border-color:var(--lime);opacity:1}}
  .thumb img{{width:100%;height:100%;object-fit:cover}}
  .thumb span{{position:absolute;bottom:5px;right:6px;background:rgba(23,35,45,.88);color:#fff;font-size:10px;padding:2px 6px;border-radius:999px}}
  #end-panel{{margin:5px 0 0;padding:20px 22px;background:#eaf2d2;border:1px solid #c8d99e;border-radius:14px;text-align:left;display:none}}
  #end-panel.active{{display:block;animation:slideIn .35s ease-out}}
  @keyframes slideIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
  #end-panel h2{{margin:0 0 4px;font-size:20px;color:var(--ink)}}
  #end-panel .sub{{color:#536044;margin:0 0 14px;font-size:13px}}
  .end-actions{{display:flex;gap:10px;flex-wrap:wrap}}
  .btn-cta{{display:inline-flex;align-items:center;gap:8px;padding:11px 18px;border-radius:10px;font-size:14px;font-weight:700;text-decoration:none;transition:transform .14s ease,background .14s ease}}
  .btn-cta.primary{{background:var(--ink);color:#fff;border:1px solid var(--ink)}}
  .btn-cta.primary:hover{{background:var(--ink-2);color:#fff;transform:translateY(-1px)}}
  .btn-cta.secondary{{background:transparent;color:var(--ink);border:1px solid #9daa7e}}
  .btn-cta.secondary:hover{{background:#dfe9c1;color:var(--ink)}}
  .btn-cta .label{{font-size:11px;opacity:.7;font-weight:500;display:block}}
  .btn-cta .title{{display:block}}
  footer{{padding:16px 20px;text-align:center;border-top:1px solid var(--line);background:var(--surface);color:var(--muted);font-size:13px}}
  footer a{{margin:0 10px}}
  #resume-banner{{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--ink);border:1px solid #42515c;border-radius:14px;padding:11px 14px;display:none;gap:12px;align-items:center;z-index:60;box-shadow:0 14px 40px rgba(23,35,45,.35);max-width:92%;flex-wrap:wrap}}
  #resume-banner.show{{display:flex}}
  #resume-banner .text{{font-size:13px;color:#cad2cf}}
  #resume-banner .text strong{{color:#fff}}
  #resume-banner button{{padding:6px 11px;font-size:13px;margin:0;background:#2b3a45;border-color:#41515d;color:#fff}}
  #resume-banner button.primary{{background:var(--signal);border-color:var(--signal);color:#fff}}
  @media(max-width:1280px){{main{{grid-template-columns:minmax(0,1fr) 340px}}aside#toc{{display:none}}aside#toc.open{{display:block;position:fixed;top:14px;left:14px;width:286px;height:calc(100vh - 28px);z-index:100;max-height:none}}}}
  @media(max-width:920px){{header .meta{{width:100%;margin-left:48px}}main{{grid-template-columns:1fr;padding:14px}}aside#transcript{{max-height:none}}}}
  @media(max-width:620px){{header{{padding:12px 14px;gap:9px}}header h1{{order:3;flex:0 0 100%;font-size:17px}}header .meta{{order:4;width:100%;margin-left:0;font-size:12px}}#progress{{padding:9px 14px;gap:8px}}#progress .label:first-child,#progress .bar:first-of-type{{display:none}}main{{display:block;width:100%;max-width:100%;padding:10px}}#stage,aside#transcript{{width:100%;max-width:100%;border-radius:13px;padding:10px}}aside#transcript{{margin-top:18px}}#slide-wrap,#tx-body,#tx-body p{{width:100%;max-width:100%}}#tx-body p{{white-space:normal;word-break:break-word}}#controls{{display:grid;grid-template-columns:1fr 1fr 1fr}}#controls button{{padding:9px 7px}}#pos{{grid-column:1/-1;text-align:center;margin:0}}.thumb{{flex-basis:104px}}}}
  @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{scroll-behavior:auto!important;animation:none!important;transition:none!important}}}}
</style>
</head>
<body class="{body_class}">
<header>
  <button class="menu-toggle" id="menu-toggle" title="{tx_menu_title}">☰</button>
  <a href="{back_href}">← {tx_home}</a>
  <h1>{title}</h1>
  <span class="meta">LOs: {lo_ids} · {slide_count}{tx_slide_unit} · {duration_min}{tx_min_unit}</span>
</header>

<div id="progress">
  <span class="label"><strong>{tx_class_label} {class_number}</strong> / {total_classes}</span>
  <div class="bar"><div class="fill" id="course-fill" style="width:{course_progress_pct}%"></div></div>
  <span class="label">{tx_slide_label} <strong id="slide-num">1</strong> / {slide_count}</span>
  <div class="bar"><div class="fill" id="slide-fill"></div></div>
</div>

<main>
  <aside id="toc">
{toc_html}  </aside>
  <div id="stage">
    <div id="slide-wrap"><img id="slide" alt="{tx_slide_label}"/></div>
    <div id="controls">
      <button id="prev">◀ {tx_prev}</button>
      <button id="play" class="play">▶ {tx_play}</button>
      <button id="next">{tx_next} ▶</button>
      <button id="speed" class="speed" title="{tx_speed_title}">1×</button>
      <span id="pos">1 / {slide_count}</span>
    </div>
    <audio id="audio" preload="auto"></audio>
    {audio_notice_html}
    <section id="end-panel">
      <h2>{tx_end_title}</h2>
      <p class="sub">{tx_end_sub}</p>
      <div class="end-actions">{end_actions_html}</div>
    </section>
  </div>
  <aside id="transcript">
    <h2>{tx_transcript_h2}</h2>
    <div id="tx-body"></div>
  </aside>
</main>

<section id="thumbs"></section>

<div id="resume-banner" role="dialog" aria-live="polite">
  <span class="text">{tx_resume_prefix}: <strong id="resume-pos">—</strong></span>
  <button id="resume-yes" class="primary">{tx_resume_yes}</button>
  <button id="resume-no">{tx_resume_no}</button>
</div>

<footer>
  <a href="{quiz_href}">{tx_quiz_cta_footer}</a>
  <a href="{back_href}">{tx_back_to_toc}</a>
</footer>

<script>
const SLIDES = {slides_json};
let current = 0;
const img = document.getElementById('slide');
const audio = document.getElementById('audio');
const txBody = document.getElementById('tx-body');
const pos = document.getElementById('pos');
const thumbs = document.getElementById('thumbs');
const btnPrev = document.getElementById('prev');
const btnPlay = document.getElementById('play');
const btnNext = document.getElementById('next');

SLIDES.forEach((s, i) => {{
  const t = document.createElement('div');
  t.className = 'thumb';
  t.dataset.i = i;
  t.innerHTML = '<img src="' + s.png + '"/><span>' + (i+1) + '</span>';
  t.onclick = () => loadSlide(i, true);
  thumbs.appendChild(t);
}});

function loadSlide(i, autoplay, resumeTime) {{
  current = Math.max(0, Math.min(SLIDES.length - 1, i));
  const s = SLIDES[current];
  img.src = s.png;
  audio.src = s.mp3;
  if (resumeTime && resumeTime > 1) {{
    audio.addEventListener('loadedmetadata', () => {{
      const dur = audio.duration;
      if (isFinite(dur)) audio.currentTime = Math.min(resumeTime, Math.max(0, dur - 1));
    }}, {{ once: true }});
  }}
  pos.textContent = (current + 1) + ' / ' + SLIDES.length;
  btnPrev.disabled = current === 0;
  btnNext.disabled = current === SLIDES.length - 1;

  txBody.innerHTML = '';
  const times = s.transcriptTimes || [];
  s.transcript.forEach((line, idx) => {{
    const p = document.createElement('p');
    p.textContent = line;
    const t = times[idx];
    if (t && typeof t.start === 'number' && typeof t.end === 'number') {{
      p.dataset.start = t.start;
      p.dataset.end = t.end;
    }}
    txBody.appendChild(p);
  }});

  document.querySelectorAll('.thumb').forEach((t, idx) => t.classList.toggle('current', idx === current));
  const cur = document.querySelector('.thumb.current');
  if (cur) {{
    const targetLeft = cur.offsetLeft - (thumbs.clientWidth - cur.clientWidth) / 2;
    thumbs.scrollTo({{left:Math.max(0, targetLeft), behavior:'smooth'}});
  }}

  maybeShowEnd();
  saveState();

  if (autoplay) audio.play().catch(() => {{}});
}}

// localStorage resume — key = page path so each class gets its own slot
const STORAGE_KEY = 'course-builder:' + location.pathname;
const STATE_MAX_AGE_MS = 30 * 86400 * 1000;
let lastSaveTs = 0;

function saveState() {{
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify({{
      slide: current,
      time: audio.currentTime || 0,
      ts: Date.now()
    }}));
  }} catch(e) {{}}
}}
function loadResumeState() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    if (Date.now() - s.ts > STATE_MAX_AGE_MS) return null;
    if (typeof s.slide !== 'number' || s.slide < 0 || s.slide >= SLIDES.length) return null;
    // Don't bother prompting if they barely started
    if (s.slide === 0 && (s.time || 0) < 3) return null;
    return s;
  }} catch(e) {{ return null; }}
}}
function clearState() {{
  try {{ localStorage.removeItem(STORAGE_KEY); }} catch(e) {{}}
}}
function fmtTime(t) {{
  const sec = Math.max(0, Math.floor(t || 0));
  return Math.floor(sec/60) + ':' + String(sec%60).padStart(2,'0');
}}

let lastActiveLine = null;
audio.addEventListener('timeupdate', () => {{
  const now = Date.now();
  if (now - lastSaveTs > 3000) {{ saveState(); lastSaveTs = now; }}
  // Highlight the transcript line whose [start, end) range contains currentTime.
  // Line timings come from char-proportional splitting of the slide's MP3 duration.
  const t = audio.currentTime;
  const lines = txBody.children;
  let newActive = null;
  for (let i = 0; i < lines.length; i++) {{
    const el = lines[i];
    const s = parseFloat(el.dataset.start);
    const e = parseFloat(el.dataset.end);
    if (!isNaN(s) && !isNaN(e) && t >= s && t < e) {{ newActive = el; break; }}
  }}
  if (newActive !== lastActiveLine) {{
    if (lastActiveLine) lastActiveLine.classList.remove('active');
    if (newActive) {{
      newActive.classList.add('active');
      newActive.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
    }}
    lastActiveLine = newActive;
  }}
}});

// Playback speed — single cycle button, global across classes
const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2];
const SPEED_KEY = 'course-builder:playback-speed';
const btnSpeed = document.getElementById('speed');

function loadSpeed() {{
  try {{
    const v = parseFloat(localStorage.getItem(SPEED_KEY));
    if (SPEEDS.includes(v)) return v;
  }} catch(e) {{}}
  return 1;
}}
function applySpeed(v) {{
  audio.playbackRate = v;
  if ('preservesPitch' in audio) audio.preservesPitch = true;
  // Display: 1× (no decimal) / 1.25× / 1.5× etc.
  btnSpeed.textContent = (Number.isInteger(v) ? v : v.toString()) + '×';
  btnSpeed.classList.toggle('speed-fast', v > 1);
  btnSpeed.classList.toggle('speed-slow', v < 1);
}}
let currentSpeed = loadSpeed();
applySpeed(currentSpeed);
btnSpeed.onclick = () => {{
  const idx = SPEEDS.indexOf(currentSpeed);
  currentSpeed = SPEEDS[(idx + 1) % SPEEDS.length];
  applySpeed(currentSpeed);
  try {{ localStorage.setItem(SPEED_KEY, String(currentSpeed)); }} catch(e) {{}}
}};
audio.addEventListener('loadedmetadata', () => {{ audio.playbackRate = currentSpeed; }});

const endPanel = document.getElementById('end-panel');
const slideFill = document.getElementById('slide-fill');
const slideNumEl = document.getElementById('slide-num');
const toc = document.getElementById('toc');
const menuToggle = document.getElementById('menu-toggle');
menuToggle.addEventListener('click', () => toc.classList.toggle('open'));

function maybeShowEnd() {{
  if (current === SLIDES.length - 1) {{
    endPanel.classList.add('active');
  }} else {{
    endPanel.classList.remove('active');
  }}
  // Update progress bar
  const pct = ((current + 1) / SLIDES.length) * 100;
  slideFill.style.width = pct + '%';
  slideNumEl.textContent = current + 1;
}}

btnPrev.onclick = () => loadSlide(current - 1, true);
btnNext.onclick = () => loadSlide(current + 1, true);
btnPlay.onclick = () => audio.paused ? audio.play() : audio.pause();

audio.addEventListener('play', () => btnPlay.textContent = '⏸ {tx_pause}');
audio.addEventListener('pause', () => btnPlay.textContent = '▶ {tx_play}');
audio.addEventListener('ended', () => {{
  if (current < SLIDES.length - 1) {{
    loadSlide(current + 1, true);
  }} else {{
    maybeShowEnd();
    endPanel.scrollIntoView({{behavior:'smooth', block:'nearest'}});
  }}
}});

document.addEventListener('keydown', (e) => {{
  if (['INPUT','TEXTAREA'].includes(e.target.tagName)) return;
  if (e.key === ' ') {{ e.preventDefault(); btnPlay.click(); }}
  else if (e.key === 'ArrowRight') btnNext.click();
  else if (e.key === 'ArrowLeft') btnPrev.click();
}});

// Initial load — show resume banner if prior state exists, otherwise start at slide 0
const resumeState = loadResumeState();
loadSlide(0, false);
if (resumeState) {{
  document.getElementById('resume-pos').textContent =
    '{tx_slide_label} ' + (resumeState.slide + 1) + ' · ' + fmtTime(resumeState.time);
  const banner = document.getElementById('resume-banner');
  banner.classList.add('show');
  document.getElementById('resume-yes').onclick = () => {{
    banner.classList.remove('show');
    loadSlide(resumeState.slide, true, resumeState.time);
  }};
  document.getElementById('resume-no').onclick = () => {{
    banner.classList.remove('show');
    clearState();
  }};
}}
</script>
</body>
</html>
"""


QUIZ_TMPL = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{section_title} · {tx_quiz_title}</title>
<style>
  :root{{--ink:#17232d;--paper:#f5f1e8;--surface:#fffdf8;--line:#d9d2c5;--muted:#6b746f;--signal:#ff5c35;--signal-dark:#d84524;--lime:#b9e34b;--focus:#376fba}}
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:"Segoe UI Variable","Segoe UI",Arial,sans-serif;background:var(--paper);color:var(--ink);line-height:1.6}}
  .wrap{{max-width:820px;margin:0 auto;padding:34px 22px 90px}}
  a{{color:var(--signal-dark);text-decoration-thickness:1px;text-underline-offset:3px}}
  a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{{outline:3px solid var(--focus);outline-offset:3px}}
  h1{{font-size:clamp(30px,5vw,48px);line-height:1.05;letter-spacing:-.04em;margin:24px 0 8px}}
  .meta{{color:var(--muted);margin-bottom:28px;font-size:14px}}
  .q{{background:var(--surface);border:1px solid var(--line);border-top:5px solid var(--ink);border-radius:16px;padding:22px;margin-bottom:18px;box-shadow:0 14px 34px rgba(23,35,45,.08)}}
  .q .tag{{display:inline-block;background:#e9e4da;color:#59625e;padding:3px 8px;border-radius:999px;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-right:5px}}
  .q h3{{margin:12px 0 16px;font-size:18px;line-height:1.45}}
  .choice{{display:flex;gap:11px;padding:12px 13px;border:1px solid var(--line);border-radius:10px;margin-bottom:8px;cursor:pointer;align-items:flex-start;transition:background .14s ease,border-color .14s ease,transform .14s ease}}
  .choice:hover{{background:#f2ede3;border-color:#bfb6a7;transform:translateX(2px)}}
  .choice input{{margin-top:5px;accent-color:var(--signal)}}
  .choice.correct{{border-color:#70922a;background:#eaf2d2}}
  .choice.wrong{{border-color:#c4533a;background:#fff0ea}}
  textarea{{width:100%;background:#fff;color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:12px;font:inherit;font-size:14px;min-height:100px}}
  .submit{{background:var(--signal);border:1px solid var(--signal);color:#fff;padding:13px 26px;border-radius:10px;font:inherit;font-size:15px;font-weight:750;cursor:pointer;margin-top:12px}}
  .submit:hover{{background:var(--signal-dark);border-color:var(--signal-dark)}}
  .explain{{background:#eaf2d2;border-left:4px solid #70922a;padding:12px 14px;margin-top:12px;border-radius:8px;font-size:14px;display:none}}
  .explain.show{{display:block}}
  .score{{position:sticky;top:0;background:var(--ink);color:#fff;padding:13px 16px;border-radius:10px;font-size:15px;z-index:10;box-shadow:0 8px 22px rgba(23,35,45,.18)}}
  .nav{{margin-bottom:16px}}
  ul{{margin:6px 0 0 18px;padding:0}}li{{margin:4px 0}}
  @media(max-width:600px){{.wrap{{padding:22px 14px 70px}}.q{{padding:17px;border-radius:13px}}}}
  @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;transition:none!important}}}}
</style>
</head>
<body>
<div class="wrap">
  <div class="nav"><a href="{back_href}">← {tx_back_toc_short}</a></div>
  <h1>{section_title} · {tx_quiz_title}</h1>
  <p class="meta">{n_items} {tx_items_unit} · Bloom: {bloom_summary}</p>
  <div class="score" id="score" style="display:none"></div>
  <form id="quiz">
{items_html}
    <button type="button" class="submit" id="submit-btn">{tx_submit_grade}</button>
  </form>
  <div id="next-step" style="display:none;margin-top:24px;text-align:center"></div>
</div>
<script>
const ITEMS = {items_json};
const NEXT_HREF = {next_href_json};
const NEXT_TITLE = {next_title_json};
const BACK_HREF = {back_href_json};
const scoreEl = document.getElementById('score');

document.getElementById('submit-btn').onclick = () => {{
  let correct = 0;
  ITEMS.forEach((item, idx) => {{
    const q = document.getElementById('q' + idx);
    const exp = q.querySelector('.explain');
    if (['mcq_single','mcq_multi','true_false'].includes(item.type)) {{
      const picked = [...q.querySelectorAll('input:checked')].map(i => i.value).sort();
      const ans = [...item.correct].sort();
      const ok = JSON.stringify(picked) === JSON.stringify(ans);
      if (ok) correct++;
      q.querySelectorAll('.choice').forEach(c => {{
        const v = c.querySelector('input').value;
        if (ans.includes(v)) c.classList.add('correct');
        else if (picked.includes(v)) c.classList.add('wrong');
      }});
    }}
    exp.classList.add('show');
  }});
  const gradable = ITEMS.filter(i => i.type !== 'short_answer').length;
  scoreEl.style.display = 'block';
  scoreEl.innerHTML = '<strong>' + correct + ' / ' + gradable + '</strong> {tx_score_correct}.' +
    (gradable < ITEMS.length ? ' {tx_short_answer_note_prefix}' + (ITEMS.length - gradable) + '{tx_short_answer_note_mid})' : '');

  const nextStep = document.getElementById('next-step');
  let html = '';
  if (NEXT_HREF) {{
    html = '<a href="' + NEXT_HREF + '" style="display:inline-block;padding:12px 24px;background:#17232d;color:#fff;border-radius:10px;font-weight:700;text-decoration:none;margin-right:10px">▶ {tx_next_label}: ' + NEXT_TITLE + '</a>';
  }}
  html += '<a href="' + BACK_HREF + '" style="display:inline-block;padding:12px 24px;background:transparent;color:#17232d;border:1px solid #9f988b;border-radius:10px;text-decoration:none">{tx_back_to_toc}</a>';
  nextStep.innerHTML = html;
  nextStep.style.display = 'block';

  window.scrollTo({{top:0, behavior:'smooth'}});
}};
</script>
</body>
</html>
"""


def render_quiz_item_html(item: dict, idx: int, lang: str = "ko") -> str:
    t = _tx(lang)
    stem = html.escape(item["stem"])
    bloom = html.escape(item.get("bloom", ""))
    itype = item["type"]
    parts = [
        f'<div class="q" id="q{idx}">',
        f'  <span class="tag">Q{idx+1}</span>',
        f'  <span class="tag">{bloom}</span>',
        f'  <span class="tag">{itype}</span>',
        f'  <h3>{stem}</h3>',
    ]
    if itype in ("mcq_single", "mcq_multi"):
        input_type = "radio" if itype == "mcq_single" else "checkbox"
        for i, choice in enumerate(item["choices"]):
            letter = chr(ord("A") + i)
            parts.append(
                f'  <label class="choice"><input type="{input_type}" name="q{idx}" value="{letter}">'
                f'<span><strong>{letter}.</strong> {html.escape(str(choice))}</span></label>'
            )
    elif itype == "true_false":
        for letter, text in [("T", t["true_label"]), ("F", t["false_label"])]:
            parts.append(
                f'  <label class="choice"><input type="radio" name="q{idx}" value="{letter}">'
                f'<span>{text}</span></label>'
            )
    elif itype == "short_answer":
        parts.append(f'  <textarea placeholder="{t["answer_placeholder"]}"></textarea>')

    exp = html.escape(item.get("explanation", ""))
    rubric = item.get("rubric", [])
    rubric_html = ""
    if rubric:
        rubric_html = f"<strong>{t['rubric_heading']}:</strong><ul>" + \
            "".join(f"<li>{html.escape(r)}</li>" for r in rubric) + "</ul>"
    dr = item.get("distractor_rationales", {})
    dr_html = ""
    if dr:
        dr_html = f"<br><strong>{t['distractor_heading']}:</strong><ul>" + \
            "".join(f"<li><strong>{k}.</strong> {html.escape(v)}</li>" for k, v in dr.items()) + "</ul>"
    correct_txt = ", ".join(item.get("correct", []))
    parts.append(
        f'  <div class="explain">'
        + (f"<strong>{t['correct_label']}: {correct_txt}</strong><br>" if correct_txt else "")
        + f'{exp}{dr_html}{rubric_html}</div>'
    )
    parts.append('</div>')
    return "\n".join(parts)


def make_end_actions_html(next_cls_title: str | None,
                          next_cls_href: str | None,
                          is_last_in_section: bool,
                          is_last_in_course: bool,
                          quiz_href: str,
                          back_href: str,
                          lang: str = "ko") -> str:
    t = _tx(lang)
    fallback_title = t["cta_continue"]
    parts = []
    if is_last_in_course:
        # Final class → quiz + back to index
        parts.append(
            f'<a class="btn-cta primary" href="{quiz_href}">'
            f'<span><span class="label">{t["cta_this_section"]}</span>'
            f'<span class="title">{t["cta_final_quiz"]}</span></span></a>'
        )
        parts.append(
            f'<a class="btn-cta secondary" href="{back_href}">'
            f'<span><span class="label">{t["cta_done"]}</span>'
            f'<span class="title">{t["cta_course_toc"]}</span></span></a>'
        )
    elif is_last_in_section:
        # End of section → quiz is primary, first class of next section is secondary
        parts.append(
            f'<a class="btn-cta primary" href="{quiz_href}">'
            f'<span><span class="label">{t["cta_check_section"]}</span>'
            f'<span class="title">{t["cta_section_quiz"]}</span></span></a>'
        )
        if next_cls_href:
            parts.append(
                f'<a class="btn-cta secondary" href="{next_cls_href}">'
                f'<span><span class="label">{t["cta_next_section"]}</span>'
                f'<span class="title">▶ {html.escape(next_cls_title or fallback_title)}</span></span></a>'
            )
    else:
        # Next class in the same section
        if next_cls_href:
            parts.append(
                f'<a class="btn-cta primary" href="{next_cls_href}">'
                f'<span><span class="label">{t["cta_next_class"]}</span>'
                f'<span class="title">▶ {html.escape(next_cls_title or fallback_title)}</span></span></a>'
            )
        parts.append(
            f'<a class="btn-cta secondary" href="{quiz_href}">'
            f'<span><span class="label">{t["cta_check_first"]}</span>'
            f'<span class="title">{t["cta_section_quiz_short"]}</span></span></a>'
        )
    return "\n    ".join(parts)


def make_toc_html(manifest: dict, current_cls_id: str, current_sec_slug: str,
                  current_cls_slug: str, quiz_counts: dict, lang: str = "ko") -> str:
    """Render sidebar TOC with relative hrefs from current class dir."""
    t = _tx(lang)
    def class_href(sec_slug: str, cls_slug: str) -> str:
        if sec_slug == current_sec_slug:
            return f"../{cls_slug}/player.html"
        return f"../../../{sec_slug}/classes/{cls_slug}/player.html"

    def quiz_href(sec_slug: str) -> str:
        if sec_slug == current_sec_slug:
            return "../../quiz.html"
        return f"../../../{sec_slug}/quiz.html"

    lines = []
    for sec in manifest["sections"]:
        lines.append(f'    <h3>{html.escape(sec["title"])}</h3>')
        lines.append("    <ul>")
        for cls in sec["classes"]:
            cur_cls = "current" if cls["id"] == current_cls_id else ""
            lines.append(
                f'      <li class="{cur_cls}"><a href="{class_href(sec["slug"], cls["slug"])}">'
                f'{html.escape(cls["title"])}</a></li>'
            )
        if quiz_counts.get(sec["id"]):
            quiz_label = t["toc_quiz_tpl"].format(n=quiz_counts[sec["id"]])
            lines.append(
                f'      <li class="quiz"><a href="{quiz_href(sec["slug"])}">'
                f'{quiz_label}</a></li>'
            )
        lines.append("    </ul>")
    return "\n".join(lines) + "\n"


def build_class_player(cls: dict, root: Path, back_href: str, quiz_href: str,
                       next_cls_title: str | None = None,
                       next_cls_href: str | None = None,
                       is_last_in_section: bool = False,
                       is_last_in_course: bool = False,
                       class_number: int = 1,
                       total_classes: int = 1,
                       toc_html: str = "",
                       lang: str = "ko"):
    cls_rel_dir = Path(cls["assets"]["slide_source"]).parent
    cls_dir = root / cls_rel_dir

    transcript_path = cls_dir / "transcript.txt"
    slide_by = parse_transcript_by_slide(transcript_path.read_text(encoding="utf-8")) \
        if transcript_path.exists() else {}

    png_dir = cls_dir / "slides_png"
    pngs = sorted(png_dir.glob("slide.*.png")) if png_dir.exists() else []

    slides = []
    total_dur = 0.0
    for i, png in enumerate(pngs):
        n = i + 1
        mp3_file = cls_dir / "audio" / f"slide_{n:02d}.mp3"
        mp3_rel = f"audio/slide_{n:02d}.mp3" if mp3_file.exists() else ""
        slide_dur = mp3_duration(mp3_file)
        total_dur += slide_dur
        lines = slide_by.get(n, [])
        slides.append({
            "png": f"slides_png/{png.name}",
            "mp3": mp3_rel,
            "transcript": lines,
            # Parallel array: lines[k] spans transcriptTimes[k].start..end (seconds)
            # Absent (or empty) when audio is missing — JS then skips highlight.
            "transcriptTimes": char_proportional_line_times(lines, slide_dur),
        })

    has_audio = any(slide["mp3"] for slide in slides)
    duration_min = round(total_dur / 60.0, 1) if has_audio else (cls.get("duration_min") or 0)
    lo_ids = ", ".join(cls.get("lo_ids", []))
    end_actions_html = make_end_actions_html(
        next_cls_title, next_cls_href, is_last_in_section, is_last_in_course,
        quiz_href, back_href, lang=lang,
    )
    course_progress_pct = round(class_number / total_classes * 100, 1)
    t = _tx(lang)
    audio_notice_html = (
        f'<p class="ai-voice-notice">{html.escape(t["ai_voice_notice"])}</p>'
        if any(slide["mp3"] for slide in slides) else ""
    )
    tx_kwargs = {f"tx_{k}": v for k, v in t.items()}
    html_out = PLAYER_TMPL.format(
        title=html.escape(cls["title"]),
        lo_ids=html.escape(lo_ids),
        slide_count=len(slides),
        duration_min=duration_min,
        back_href=back_href,
        quiz_href=quiz_href,
        slides_json=json.dumps(slides, ensure_ascii=False),
        end_actions_html=end_actions_html,
        class_number=class_number,
        total_classes=total_classes,
        course_progress_pct=course_progress_pct,
        toc_html=toc_html,
        audio_notice_html=audio_notice_html,
        body_class="has-audio" if has_audio else "no-audio",
        lang=lang,
        **tx_kwargs,
    )
    (cls_dir / "player.html").write_text(html_out, encoding="utf-8")
    return {"slides": len(slides), "duration_min": duration_min, "lo_ids": lo_ids,
            "rel": str(cls_rel_dir)}


def build_section_quiz(sec: dict, root: Path,
                       next_sec_first_class: dict | None = None,
                       next_sec: dict | None = None,
                       lang: str = "ko") -> int:
    quiz_path_rel = sec.get("quiz_path") or f"sections/{sec['slug']}/quiz.json"
    quiz_json_path = root / quiz_path_rel
    if not quiz_json_path.exists():
        return 0
    qdata = json.loads(quiz_json_path.read_text(encoding="utf-8"))
    items = qdata["items"]
    items_html = "\n".join(render_quiz_item_html(it, i, lang) for i, it in enumerate(items))
    bloom = qdata.get("bloom_distribution", {})
    bloom_summary = ", ".join(f"{k}:{v}" for k, v in bloom.items())
    t = _tx(lang)
    # After-quiz navigation: to next section's first class player
    if next_sec and next_sec_first_class:
        next_href = f"../{next_sec['slug']}/classes/{next_sec_first_class['slug']}/player.html"
        next_title = next_sec_first_class.get("title", t["cta_next_class"])
    else:
        next_href = None
        next_title = None
    tx_kwargs = {f"tx_{k}": v for k, v in t.items()}
    out = QUIZ_TMPL.format(
        section_title=html.escape(sec["title"]),
        n_items=len(items),
        bloom_summary=html.escape(bloom_summary),
        back_href="../../index.html",
        items_html=items_html,
        items_json=json.dumps(items, ensure_ascii=False),
        next_href_json=json.dumps(next_href),
        next_title_json=json.dumps(next_title, ensure_ascii=False),
        back_href_json=json.dumps("../../index.html"),
        lang=lang,
        **tx_kwargs,
    )
    (quiz_json_path.parent / "quiz.html").write_text(out, encoding="utf-8")
    return len(items)


INDEX_STYLE = """
:root{--ink:#17232d;--paper:#f5f1e8;--surface:#fffdf8;--line:#d9d2c5;--muted:#6b746f;--signal:#ff5c35;--lime:#b9e34b}
*{box-sizing:border-box}
body{font-family:"Segoe UI Variable","Segoe UI",Arial,sans-serif;max-width:900px;margin:0 auto;padding:58px 24px 90px;background:var(--paper);color:var(--ink);line-height:1.6}
body::before{content:"CHATGPT · ОТ А ДО Я";display:inline-block;background:var(--ink);color:#fff;padding:6px 10px;border-radius:999px;font-size:11px;font-weight:750;letter-spacing:.11em}
a{color:var(--ink);text-decoration:none}a:hover{color:#d84524}
a:focus-visible{outline:3px solid #376fba;outline-offset:3px}
h1{font-size:clamp(38px,7vw,68px);line-height:.98;letter-spacing:-.05em;margin:24px 0 16px;max-width:760px}
h2{font-size:21px;margin:42px 0 12px;padding:0 0 9px;border-bottom:4px solid var(--signal);letter-spacing:-.02em}
ul{list-style:none;padding:0;margin:0;display:grid;gap:9px}
li{padding:15px 16px;background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 20px rgba(23,35,45,.05)}
li a{font-weight:700}
.los{color:var(--muted);font-size:13px;margin-left:8px}
.quiz-link{color:#58751c;font-weight:750}
.meta{color:var(--muted);margin-bottom:30px;max-width:760px}
@media(max-width:600px){body{padding:34px 14px 70px}.los{display:block;margin:5px 0 0}}
"""


def audience_to_str(aud) -> str:
    """Coerce audience field (string or dict) into a short display string."""
    if isinstance(aud, str):
        return aud
    if isinstance(aud, dict):
        parts = []
        if aud.get("profile"):
            parts.append(str(aud["profile"]))
        if aud.get("level"):
            parts.append(f"({aud['level']})")
        return " ".join(parts) if parts else json.dumps(aud, ensure_ascii=False)[:80]
    return str(aud)


def build_index(manifest: dict, per_class_info: list, quiz_counts: dict, root: Path,
                lang: str = "ko"):
    topic = manifest["course"]["topic"]
    audience = audience_to_str(manifest["course"].get("audience", ""))
    t = _tx(lang)
    stats_txt = t["landing_stats_tpl"].format(
        n_cls=manifest["stats"]["classes"],
        n_lo=manifest["stats"]["lo_count"],
        mins=manifest["stats"].get("actual_audio_duration_sec", 0) / 60.0,
    )
    lines = [
        f'<!DOCTYPE html><html lang="{lang}"><head>',
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{html.escape(topic)}</title>',
        f'<style>{INDEX_STYLE}</style>',
        '</head><body>',
        f'<h1>{html.escape(topic)}</h1>',
        f'<p class="meta">{html.escape(audience)} · '
        f'{manifest["course"]["language"]} · {html.escape(stats_txt)}</p>',
    ]
    for sec in manifest["sections"]:
        lines.append(f'<h2>{html.escape(sec["title"])}</h2><ul>')
        for cls in sec["classes"]:
            info = next(pc for pc in per_class_info if pc["rel"] == str(Path(cls["assets"]["slide_source"]).parent))
            class_stats = t["landing_class_stats_tpl"].format(
                n_slides=info["slides"], dur=info["duration_min"], los=info["lo_ids"],
            )
            lines.append(
                f'<li><a href="{info["rel"]}/player.html">{html.escape(cls["title"])}</a>'
                f'<span class="los">{html.escape(class_stats)}</span></li>'
            )
        if sec["id"] in quiz_counts:
            quiz_label = t["toc_quiz_tpl"].format(n=quiz_counts[sec["id"]])
            lines.append(
                f'<li><a href="sections/{sec["slug"]}/quiz.html" class="quiz-link">'
                    f'{html.escape(quiz_label)}</a></li>'
            )
        lines.append('</ul>')
    lines.append('</body></html>')
    (root / "index.html").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("course_root", type=Path)
    args = ap.parse_args()
    root = args.course_root
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    lang = (manifest.get("course", {}) or {}).get("language", "ko")
    if lang not in _PLAYER_STRINGS:
        lang = "ko"

    per_class_info = []
    quiz_counts = {}

    # Flatten class traversal to compute next-class pointers
    flat = []
    for sec_idx, sec in enumerate(manifest["sections"]):
        for cls_idx, cls in enumerate(sec["classes"]):
            flat.append({
                "sec": sec,
                "sec_idx": sec_idx,
                "cls": cls,
                "cls_idx": cls_idx,
                "is_last_in_section": cls_idx == len(sec["classes"]) - 1,
            })
    for i, entry in enumerate(flat):
        entry["is_last_in_course"] = (i == len(flat) - 1)
        entry["next"] = flat[i + 1] if i + 1 < len(flat) else None

    def path_to_next(entry) -> tuple[str | None, str | None]:
        nxt = entry["next"]
        if not nxt:
            return (None, None)
        # Current class dir: sections/<sec>/classes/<cls>/
        # Next class dir:    sections/<nxt_sec>/classes/<nxt_cls>/
        # Relative from current to next:
        if nxt["sec"]["id"] == entry["sec"]["id"]:
            rel = f"../{nxt['cls']['slug']}/player.html"
        else:
            rel = f"../../../{nxt['sec']['slug']}/classes/{nxt['cls']['slug']}/player.html"
        return (nxt["cls"]["title"], rel)

    # Count quiz items per section first (TOC sidebar needs them)
    for sec in manifest["sections"]:
        qp = root / (sec.get("quiz_path") or f"sections/{sec['slug']}/quiz.json")
        if qp.exists():
            try:
                quiz_counts[sec["id"]] = len(json.loads(qp.read_text(encoding="utf-8")).get("items", []))
            except Exception:
                pass

    total_classes = len(flat)
    for idx, entry in enumerate(flat, start=1):
        nxt_title, nxt_href = path_to_next(entry)
        toc_html = make_toc_html(
            manifest,
            current_cls_id=entry["cls"]["id"],
            current_sec_slug=entry["sec"]["slug"],
            current_cls_slug=entry["cls"]["slug"],
            quiz_counts=quiz_counts,
            lang=lang,
        )
        info = build_class_player(
            entry["cls"], root,
            back_href="../../../../index.html",
            quiz_href="../../quiz.html",
            next_cls_title=nxt_title,
            next_cls_href=nxt_href,
            is_last_in_section=entry["is_last_in_section"],
            is_last_in_course=entry["is_last_in_course"],
            class_number=idx,
            total_classes=total_classes,
            toc_html=toc_html,
            lang=lang,
        )
        per_class_info.append(info)

    # Render section quiz HTML
    sections = manifest["sections"]
    for i, sec in enumerate(sections):
        next_sec = sections[i + 1] if i + 1 < len(sections) else None
        next_first = next_sec["classes"][0] if (next_sec and next_sec.get("classes")) else None
        build_section_quiz(sec, root, next_sec_first_class=next_first, next_sec=next_sec, lang=lang)

    build_index(manifest, per_class_info, quiz_counts, root, lang=lang)
    print(f"✓ Generated index.html + {len(per_class_info)} player.html + {len(quiz_counts)} quiz.html")


if __name__ == "__main__":
    main()
