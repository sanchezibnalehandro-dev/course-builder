---
name: script-writing
description: Write TTS-ready transcripts with [slide N] cues, [pause:ms] markers, and optional SSML. Convert raw code/URLs/long numbers to speakable forms. Use when turning slides+beats into a narrator script. Triggered by the script-writer agent.
---

# Script Writing — Speakable Transcript

transcript는 **귀로 듣는 콘텐츠**다. note를 그대로 낭독하면 부자연스럽다. 문장 길이, 리듬, 호흡, 강조를 음성 기준으로 재설계.

## 구조 (plain text)

```
[slide 1]
첫 문장. 리듬을 위한 짧은 문장.
[pause:400]
두 번째 문장은 조금 더 길어도 괜찮지만 25 단어를 넘지 않도록 합니다.
[pause:600]
핵심 강조 전에는 조금 더 쉬어줍니다.

[slide 2]
새 슬라이드로 넘어갑니다.
...
```

### Line layout (subtitle-sync 필수)
**한 슬라이드의 내레이션을 절대 한 줄에 몰아넣지 말 것.** `generate-player.py`의 `parse_transcript_by_slide`는 newline으로 분할해 각 줄을 자막 추적 단위로 사용하고, `char_proportional_line_times`가 각 줄의 글자 수 비율로 슬라이드 MP3 duration을 쪼개 `{start,end}`를 부여한다. 한 줄짜리 슬라이드는 자막 한 덩어리 + 하이라이트 불가.

규칙:
- **발화 단위 한 개 = 한 줄.** 문장 또는 `[pause:…]` 사이의 한 호흡 단위.
- `[pause:NNN]` 마커는 **자기만의 줄**에 둔다 (인라인 금지). 플레이어가 pause 줄은 strip → 빈 줄로 필터링.
- `[slide N]` 역시 자기만의 줄.
- 빈 줄은 슬라이드 사이 구분용으로만 허용.

❌ 금지 (한 줄에 몰아쓰기 — 추적 불가):
```
[slide 1]
첫 문장. [pause:400] 두 번째 문장. [pause:600] 세 번째 문장.
```

✅ 올바름 (줄 단위 분할 — 추적 가능):
```
[slide 1]
첫 문장.
[pause:400]
두 번째 문장.
[pause:600]
세 번째 문장.
```

## 규칙

### 문장 길이
- 영어·러시아어 ≤25단어, 한국어 ≤20어절
- 한 호흡에 읽을 수 있는 길이

### 축약·구어체 허용
- "그래서 이게 뭐냐면", "이게 꽤 중요합니다"
- 너무 문어적 표현 지양 ("기인한다" → "때문입니다")

### Cue와 Marker

| 태그 | 용도 | 예 |
|------|------|-----|
| `[slide N]` | TTS 후처리 시 오디오 구간 분할 | `[slide 3]` |
| `[pause:ms]` | 문장 사이 호흡 | `[pause:400]` |
| `[emph]...[/emph]` | 강조 (SSML 변환 시 emphasis) | `[emph]중요[/emph]` |

pause 권장값:
- 문장 사이: 300~400ms
- 문단 전환: 600~800ms
- 강조/질문 후: 800~1200ms
- 슬라이드 전환 후 첫 문장 앞: 500ms

## Unspeakable 변환 (핵심)

### Raw code literal → 설명형
- ❌ `const x = () => { return 1; }`
- ✅ "const 키워드로 x를 선언하고, 화살표 함수로 1을 반환합니다"

### 긴 숫자 → 구어
- ❌ "3.14159265358979"
- ✅ "파이, 약 3.14"
- ❌ "403,825개"
- ✅ "약 40만 개"

### URL → 이름
- ❌ "https://react.dev/learn/server-components"
- ✅ "React 공식 문서의 서버 컴포넌트 페이지"

### 심볼·이모지 → 설명 또는 제거
- ❌ "Use 👉 this"
- ✅ "이것을 사용하세요"

## Расчёт длительности

### Русский transcript: единственный duration contract

Для обычной русской учебной речи используется темп **130 произносимых слов в минуту**. TTS engine, voice, speed, chars/sec и prior-run calibration не участвуют в этой оценке.

```
spoken_sec = spoken_words / 130 × 60
estimated_duration_sec = spoken_sec + explicit_pause_sec
```

`spoken_words` считает только произносимые слова; `[slide N]`, `[pause:N]` и служебные теги не считаются. `explicit_pause_sec` — точная сумма всех pause markers.

Сначала напишите речь, необходимую для LO, `key_points` и конкретного примера, затем добавьте только естественные паузы. Измерьте получившийся урок по формуле выше. Число слов — результат содержания, а не обратный расчёт из планового времени. Самостоятельное действие ученика в practice не входит в playback duration.

Не применяйте норму слов или секунд «на слайд». По `<!-- beat: bN -->` сопоставьте каждый transcript slide block с beat sheet; несколько слайдов одного beat агрегируются.

Для каждого beat отдельно:

```
beat_spoken_sec = beat_spoken_words / 130 × 60
beat_estimated_sec = beat_spoken_sec + beat_pause_sec
```

`beat.duration_sec` и `target_duration_sec` — предварительные бюджеты. Расхождение фиксируйте в ledger, но не устраняйте его добавлением повторов или пауз. Если отсутствуют LO, `key_points` или требуемые шаги примера — допишите только недостающее содержание. Если они покрыты и practice выполнима, передайте фактическую оценку class planner для пересчёта существующих beat/class duration-полей; после согласования class total проверяется против уточнённого `target_duration_sec ±10%`.

### Паузы во всех beat-ах

- Содержание материализуется произносимой речью, покрывающей `key_points` соответствующего beat.
- Любая естественная `[pause:N]`, включая practice, не превышает 1200 мс.
- Сумма всех пауз не превышает 15% оценочной playback duration beat, а не его устаревшего планового бюджета.
- Пауза не засчитывается как самостоятельное учебное содержание и не может использоваться для заполнения недостающего текста.

### Practice

Practice содержит реальную произносимую инструкцию и проверку, но самостоятельное время ученика не является временем воспроизведения. Внутри того же beat обязателен порядок:

1. **Instruction:** назвать действие ученика, материал или объект работы и ожидаемый результат либо критерий завершения.
2. **Learner-controlled pause:** явно предложить поставить урок на паузу, выполнить действие и затем возобновить воспроизведение. Не кодировать это время маркером `[pause:N]` и не прибавлять его к duration.
3. **Continuation:** после точки возобновления произнести способ самопроверки, следующий шаг или явный переход к следующему beat. Между instruction и continuation допустима только короткая естественная пауза по общим правилам.

Practice без конкретного действия, ожидаемого результата, явной команды приостановить и возобновить урок или последующей самопроверки считается неполным. В отчёте script-writer укажите per-beat ledger и для practice — тексты instruction, learner-controlled pause и continuation.

## [slide N] 매핑

slide.source.md의 슬라이드 번호 순서와 정확히 일치해야 한다.
- 슬라이드 1 = 제목 슬라이드 (언급하고 넘어감, 20~30s)
- 슬라이드 N = recap (강조하며 마무리)

coherence-reviewer는 이 매핑을 검증한다.

## SSML 변형

사용자가 요청하거나 `language != ko`일 때 `transcript.ssml` 추가 생성.

```xml
<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.1" xml:lang="ko-KR">
  <p>
    <s>첫 문장입니다.</s>
    <break time="400ms"/>
    <s>다음 문장은 조금 <emphasis level="moderate">강조</emphasis>합니다.</s>
  </p>
</speak>
```

- `<speak>` 루트, `xml:lang` 필수
- `[pause:X]` → `<break time="Xms"/>`
- `[emph]X[/emph]` → `<emphasis level="moderate">X</emphasis>`
- `[slide N]` → SSML에서는 `<mark name="slide_N"/>`로 변환

`scripts/validate-ssml.sh`로 W3C SSML 1.1 스키마 검증.

## Speaker affect 반영
class-planner의 `speaker_affect` 필드를 문체·속도에 반영:
- `호기심`: 질문 끝 억양, 짧은 문장
- `단호`: 명사형 종결, 중간 pause 최소
- `친근`: 축약 적극, 감탄사 OK
- `엄숙`: 장문, 수식어 절제

## 재실행 규칙
- slide 수 변경되면 [slide N] 전체 재매핑
- 톤 변경은 전체 재작성 (부분 교체하면 위화감)

## 체크리스트
- [ ] 모든 문장 ≤25단어 (한국어 ≤20어절)
- [ ] raw code/긴 숫자/URL 없음
- [ ] `[slide N]` cue 수 == slide.source.md 슬라이드 수
- [ ] **각 슬라이드 내레이션이 여러 줄로 분할됨 (한 줄에 몰아쓰기 금지) — subtitle-sync 추적 가능성**
- [ ] `[pause:NNN]` 마커는 각자 자기 줄에 단독 (인라인 금지)
- [ ] Для `ru` каждый beat измерен; если полный урок расходится с планом, ledger передан class planner, а согласованный class total находится в уточнённом target ±10%
- [ ] В каждом beat каждая пауза ≤1,2 с, а сумма пауз ≤15% оценочного playback времени beat
- [ ] Каждый practice имеет порядок instruction → learner-controlled playback pause → continuation; самостоятельное время не записано как `[pause:N]`
- [ ] tone 파라미터 일관 유지
- [ ] SSML 생성 시 xsd 검증 통과
