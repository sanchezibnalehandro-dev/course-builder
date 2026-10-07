---
name: class-planning
description: Plan a single class as a beat sheet (hook → teach → example → practice → recap) used jointly by slide, note, and script authors. Use when turning a class spec into beats, allocating duration across beats, or assigning visual/speaker cues. Triggered by the class-planner agent.
---

# Class Planning — Beat Sheet Design

beat sheet는 slide/note/script 3저자의 **공유 계획**이다. 3명이 같은 내용을 다른 매체로 표현하기 때문에, beat가 모호하면 세 자산이 어긋난다.

## 5부 구조

| Beat | 목적 | 비중 (12분 class 기준) |
|------|------|----------------------|
| hook | 학습자 주의 포착, 왜 중요한지 | 45~90s |
| teach | 핵심 개념 전달, 2~3 서브토픽 | 4~6min |
| example | 구체 코드/사례로 추상을 구체화 | 2~4min |
| practice | 미니 자가학습 (퀴즈와 별개); 표의 시간은 발화 안내·확인만 포함 | 30~90s |
| recap | 핵심 3개 요약 | 30s |

위 시간은 12분 class의 초기 예시이지 발화 quota가 아니다. Duration이 8분 이하면 practice는 생략 가능하지만, Apply LO에 필요한 실제 연습은 길이를 이유로 삭제하지 않는다. 15분 초과면 teach를 2~3 beat로 더 쪼갠다.

## Beat 작성 필드

```json
{
  "id": "b1",
  "type": "hook" | "teach" | "example" | "practice" | "recap",
  "duration_sec": 45,
  "key_points": ["핵심1","핵심2","핵심3"],
  "lo_ids": ["LO-1.1"],
  "examples": [{"lang":"js","snippet":"...","why":"..."}],
  "visual_hint": "대조 다이어그램" | "code highlight" | "flowchart" | null,
  "speaker_affect": "호기심" | "단호" | "친근" | "엄숙"
}
```

## key_points 작성 원칙
- **문장이 아니라 요점** (5~12 단어)
- 각 key_point는 slide 1 bullet 또는 note 1 단락 또는 필요한 만큼의 script 설명에 대응; 초 단위 발화 quota는 아니다.
- 추상 개념만 나열하지 말고 **1개 이상 구체 예시**를 포함

## Beat type별 가이드

### hook
- 학습자가 "이거 몰랐네" 느낄 문제 제시
- 정답 노출 금지 (teach에서 해소)
- **나쁜 예**: "오늘은 RSC를 배우겠습니다"
- **좋은 예**: "이 페이지 로드가 왜 3초나 걸릴까요? 범인은 의외로..."

### teach
- 개념 정의 → 속성 2~3개 → 왜 중요 (3단 구조)
- 서브토픽이 3개 이상이면 beat 분할

### example
- 실행 가능한 코드 또는 현실 사례
- "왜 이 예시냐"를 `why` 필드에 명시 (저자들이 설명 재현할 때 참조)

### practice
- 사지선다가 아니라 **open question**
- 답은 제공하지 않음 (다음 beat에서 간접적으로 제시)
- Дайте выполнимую инструкцию и критерий результата. Если ученику нужно самостоятельное время, предложите поставить урок на паузу и продолжить после выполнения; это время не входит в `duration_sec` и не кодируется аудиотишиной.

### recap
- 정확히 3개 핵심 bullet
- 다음 class의 teaser가 있으면 가산점

## visual_hint (slide-author 힌트)
- 추상 개념 → "비교 표" or "대조 다이어그램"
- 프로세스 → "flowchart"
- 코드 → "code highlight with arrow"
- 수치·비율 → "bar chart"

## speaker_affect (script-writer 힌트)
class의 `tone` 파라미터 위에서 beat별 세부 조정:
- hook: `호기심`, `약간 미스터리`
- teach: `차분`, `명료`
- example: `흥분 섞인 설명`
- practice: `질문하는 톤`; самостоятельная работа — через learner-controlled pause, не длинную тишину в audio
- recap: `힘 실린 확신`

## Duration 검증
```
sum(beats.duration_sec) ∈ [target_sec × 0.9, target_sec × 1.1]
```
초기 계획에서 초과 시 중복을 줄이고 핵심 내용이 빠졌는지 확인한다. 부족 시 LO·예시의 실제 누락을 확인한다. 완전한 내용이 더 짧으면 시간을 채우지 않고 아래 절차로 계획을 갱신한다.

Сверка после содержательно полного transcript: оцените длительность каждого beat как русскую речь при 130 слов/мин плюс только короткие естественные явные паузы. Самостоятельное время practice исключите. Запишите эту оценку в существующий `beats[].duration_sec`, обновите `target_duration_sec` по сумме beat-ов и передайте новое class время section designer для уточнения `duration_min`. Итог курса, уже утверждённый пользователем, меняется только через существующий HITL checkpoint. Проверка суммы beat-ов против class target остаётся проверкой согласованности плана, не указанием дописывать речь.

## LO 매핑 규칙
- 모든 beat는 ≥1 LO 참조
- LO 없는 beat는 **잡담**이므로 삭제
- recap은 class의 모든 LO를 커버해야 함

## 재실행 규칙
- beat id 재번호 금지
- 구조 유지한 채 key_points만 교체 가능
- 단순 재배분은 class 총합을 보존한다. 완전한 transcript에 따른 재평가는 beat와 class 총합을 함께 갱신할 수 있다.

## 체크리스트
- [ ] 5부 구조 유지 (practice는 선택)
- [ ] sum(duration_sec) ≈ target ±10%
- [ ] 모든 beat에 lo_ids 존재
- [ ] hook이 teach의 정답을 노출하지 않음
- [ ] example beat에 실행/참조 가능한 구체 사례
- [ ] recap이 정확히 3개 핵심
