# CUE — ADR-030 v2.1 / A-2b-2 Classification Rule — RATIFIED v1.1

**작성자**: CUE · **작성일**: 2026-08-28 (v1) · **v1.1**: 2026-08-28
**상태**: **RATIFIED** — HQ가 OPEN-1~6 전부 CUE 권고안대로 비준 (2026-08-28)
**대상 필드**: M2(`NAE/pipeline/registration/state/source_manifest.yaml`) 의
`content_genre` · `theological_category` · `tradition`
**baseline**: `dev/dbma-engine` @ `1fa6fce` (A-2b-1 완료)

> 이 문서는 **분류 규칙**(§3) + 그 규칙을 14개 M2 소스에 적용한 **확정표**(§4·§4.1)를 담는다.
> **확정표는 HQ 비준됨.** 다음: **A-2b-2 EXEC 명령**으로 §4.1 을 **verbatim** backfill → CUE 독립검증.
> 진행: ① 규칙(§3) ✅ → ② 적용(§4) ✅ → ③ HQ 비준(§6) ✅ → **④ backfill (다음)** → ⑤ CUE 독립검증.

---

## 1. 왜 규칙을 먼저 고정하는가

`content_genre` / `theological_category` / `tradition` 은 단순 태그가 아니라 **Source Registry(M2)의
거버넌스 필드**다. 향후 다음에 쓰일 수 있다:

- **검색 범위 제어** — "이번 설교 연구는 confession + ecclesiology 만" 같은 scope 필터
- **retrieval 필터링** — 특정 genre/전통만 근거로 허용
- **신학적 범위 통제** — Particular vs Evangelical Baptist 자료의 프롬프트 내 가중

따라서 **임의적 LLM 분류값을 레코드에 박아 넣으면 안 된다.** 값은 (a) 고정된 controlled vocabulary 안에서,
(b) 문서의 **객관적 서지 정체성**(작품의 형식·주제·저자의 전통 계보)에 근거한 **결정 규칙**으로 정해져야 하며,
(c) 판단이 필요한 경계 사례는 HQ가 결정한다.

---

## 2. 기존 vocabulary (repo 실측 — 신규 발명 아님)

### 2.1 `content_genre` — `array[string]`, 최소 1개
근거: `resources/theological_sources/source_manifest.schema.yaml` (`NAE_METADATA_POLICY_v1.md §5` 재사용)

| 값 | 의미 |
|---|---|
| `confession` | 신앙고백서·신조·교리문답 |
| `theology` | 조직·논쟁·변증 신학 논고 |
| `history` | 역사 서술 |
| `commentary` | 성경 주석·강해 |
| `sermon` | 설교(집) |
| `mission` | 선교 신학·선교사 저술 |
| `church_practice` | 교회 질서·행정·정치(polity) 매뉴얼 |
| `pastoral` | 목회 실천·제자훈련·영성 |

### 2.2 `theological_category` — `array[string]`, 최소 1개 (스키마상 `required: false`)
근거: 동 스키마 (`NAE-SOURCE-003`)

| 값 | 의미 |
|---|---|
| `confession` | 신앙고백 주제 |
| `ecclesiology` | 교회론 |
| `soteriology` | 구원론 |
| `missions` | 선교론 |

> **4값 vocab 고정** (OPEN-1 비준). 이 4개 중 어느 것도 해당하지 않는 소스는 **키 생략**.

### 2.3 `tradition` — `string` (강제 enum 아님, 3개 canonical 표기)
근거: 동 스키마 (`NAE-SOURCE-003`)

| 값 | 의미 |
|---|---|
| `"Particular Baptist"` | 칼빈주의 계열 |
| `"American Baptist"` | 미국에서 독자 형성된 계열 |
| `"Baptist Evangelical"` | General/초기 아르미니안 계열 및 부흥운동 계열 |

### 2.4 이미 채워진 실사례 (repo)
`resources/theological_sources/baptist/source_manifest.yaml` — 1689 신앙고백:
`content_genre: [confession]` · `tradition: "Particular Baptist"` ·
`theological_category: [confession, ecclesiology, soteriology]`

---

## 3. 판정 규칙 (RATIFIED)

각 필드는 **독립적으로**, 아래 결정 절차로 값을 정한다. LLM에게 "분류해줘" 하지 않는다 —
작품의 서지 사실에서 규칙으로 도출한다.

### R-CG (content_genre)
1. **작품의 1차 형식**을 서지 정보(제목·부제·목차·판본 설명)로 판정한다.
2. 대응표:
   - 신앙고백/신조/교리문답 → `confession`
   - 조직/논쟁/변증 논고 → `theology`
   - 역사 서술 → `history`
   - 성경 본문의 절별/장별 주해·강해 → `commentary`
   - 설교 모음 → `sermon`
   - 선교 신학/선교사 서신·보고 → `mission`
   - 교회 질서·행정·정치 매뉴얼 → `church_practice`
   - 목회 실천·영성·제자훈련 → `pastoral`
3. 한 작품이 복수 형식을 실질적으로 담으면 **모두** 넣되(예: 잡문집), **부수적** 요소는 넣지 않는다.
   **다중값 상한 3개, 주형식 우선** (OPEN-5 비준).
4. 사전/렉시콘류 → `commentary` (참고 성격; `reference` 값 신설 안 함 — OPEN-2 비준).

### R-TC (theological_category)
1. 작품이 **주로 다루는 교리 자리(locus)** 를 판정한다.
2. §2.2 4값 중 해당하는 것을 **모두** 넣는다.
3. **4값 중 어느 것도 해당하지 않으면 키를 생략**한다 (WARNING-first, ADR §7.5). 억지로 끼워 넣지 않는다.
   (예: Genesis 강해, 요한계시록 강해, 일반 변증서, 성경사전 → 생략.)

### R-TR (tradition)
1. **저자/작품의 고백적 계보**(역사적 사실, 판단 아님)로 판정한다.
2. Dagg·Fuller·Hiscox — 19세기 영·미 침례교 칼빈주의 계열 → `"Particular Baptist"` (OPEN-3 비준).
3. Smith(William Smith, 성공회 학자, 비침례교 저술) → **tradition 키 생략** (OPEN-4 비준).
   `authority_class=reference` 가 참고 성격을 이미 표시한다.

---

## 4. 14개 M2 소스 적용 (RATIFIED — HQ 2026-08-28)

각 행: 확정값 + 근거(서지). 경계 사례는 **보수적으로 키 생략**(WARNING).
`(생략)` = 해당 필드 키를 M2 레코드에 넣지 않음.

| # | source_id | 작품 (형식) | content_genre | theological_category | tradition |
|---|---|---|---|---|---|
| 1 | `BAP-CHURCH-DAGG-001` | Dagg, *Church Order* (1871) — 침례교 교회정치 매뉴얼 | `[church_practice]` | `[ecclesiology]` | `Particular Baptist` |
| 2 | `BAP-CHURCH-HISCOX` | Hiscox, *Standard Manual for Baptist Churches* (1890) — 교회 행정·운영 매뉴얼 | `[church_practice, pastoral]` | `[ecclesiology]` | `Particular Baptist` |
| 3 | `BAP-MISS-FULLER-VOL01` | Fuller, Works v1 — *The Gospel Worthy of All Acceptation* (구원론 논고) | `[theology]` | `[soteriology]` | `Particular Baptist` |
| 4 | `BAP-MISS-FULLER-VOL02` | Works v2 — *Calvinistic and Socinian Systems Examined* (논쟁신학) | `[theology]` | `[soteriology]` | `Particular Baptist` |
| 5 | `BAP-MISS-FULLER-VOL03` | Works v3 — *The Gospel Its Own Witness* (변증) | `[theology]` | *(생략)* | `Particular Baptist` |
| 6 | `BAP-MISS-FULLER-VOL04` | Works v4 — *Dialogues, Letters, and Essays* (잡문·서신·에세이) | `[theology]` | *(생략)* | `Particular Baptist` |
| 7 | `BAP-MISS-FULLER-VOL05` | Works v5 — *Expository Discourses on Genesis* (강해) | `[commentary]` | *(생략)* | `Particular Baptist` |
| 8 | `BAP-MISS-FULLER-VOL06` | Works v6 — *Expository Discourses on the Apocalypse* (강해) | `[commentary]` | *(생략)* | `Particular Baptist` |
| 9 | `BAP-MISS-FULLER-VOL07` | Works v7 — *Sermons on Various Subjects* (설교집) | `[sermon]` | *(생략)* | `Particular Baptist` |
| 10 | `BAP-MISS-FULLER-VOL08` | Works v8 — *Miscellanies: Magazine Papers, Sketches of Sermons, Association Letters, Tracts* | `[theology, sermon, mission]` | `[missions]` | `Particular Baptist` |
| 11 | `BAP-REF-SMITH-VOL01` | Smith, *A Dictionary of the Bible* v1 (성경사전 / 참고) | `[commentary]` | *(생략)* | *(생략)* |
| 12 | `BAP-REF-SMITH-VOL02` | Smith, *A Dictionary of the Bible* v2 | `[commentary]` | *(생략)* | *(생략)* |
| 13 | `BAP-REF-SMITH-VOL03` | Smith, *A Dictionary of the Bible* v3 | `[commentary]` | *(생략)* | *(생략)* |
| 14 | `BAP-REF-SMITH-VOL04` | Smith, *A Dictionary of the Bible* v4 | `[commentary]` | *(생략)* | *(생략)* |

**분포 (record 단위, §4.1 dict 기준):**
- `content_genre`: **14/14 populated.** 값별 레코드 수 (한 레코드가 다중값이면 각 값에 카운트):
  `church_practice` 2 (Dagg, Hiscox) · `pastoral` 1 (Hiscox) · `theology` 5 (Fuller v1–v4 단독 + v8 다중) ·
  `commentary` 6 (Fuller v5·v6 + Smith v1–v4) · `sermon` 2 (Fuller v7 단독 + v8 다중) · `mission` 1 (Fuller v8).
  단독값 `[theology]` 레코드 = **4** (Fuller v1–v4). 다중 = Hiscox `[church_practice, pastoral]`,
  Fuller v8 `[theology, sermon, mission]`.
- `theological_category`: **5/14 populated** — ecclesiology 2 (Dagg, Hiscox), soteriology 2 (Fuller v1·v2),
  missions 1 (Fuller v8). 나머지 9 키 생략.
- `tradition`: **10/14 populated** — `Particular Baptist` (Dagg, Hiscox, Fuller v1–v8). Smith v1–v4 생략.
- 삽입 라인: content_genre 14 + theological_category 5 + tradition 10 = **+29 / −0**.

> [v1.1 정정 2026-08-28] v1 초안 §4 요약의 "theology(단독) 3" 은 계수 오류였다 — §4.1 dict·§4 표는
> 처음부터 Fuller v1–v4 4개 전부 `[theology]` 로 정확했고, 요약 문장만 틀렸다. 위 문단으로 정정.

> v4·v8 은 v1 초안에서 confidence 低로 표시됐으나 HQ가 CUE 권고안대로 비준 → 위 값 확정.

---

## 4.1 확정표 — A-2b-2 EXEC backfill 원본 (verbatim)

A-2b-2 EXEC 명령이 이 dict 를 그대로 소비한다. `None` = 해당 키를 레코드에 넣지 않는다.

```python
A2B2 = {
 "BAP-CHURCH-DAGG-001":  {"content_genre": ["church_practice"],            "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
 "BAP-CHURCH-HISCOX":     {"content_genre": ["church_practice", "pastoral"],"theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL01": {"content_genre": ["theology"],                   "theological_category": ["soteriology"],  "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL02": {"content_genre": ["theology"],                   "theological_category": ["soteriology"],  "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL03": {"content_genre": ["theology"],                   "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL04": {"content_genre": ["theology"],                   "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL05": {"content_genre": ["commentary"],                 "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL06": {"content_genre": ["commentary"],                 "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL07": {"content_genre": ["sermon"],                     "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL08": {"content_genre": ["theology", "sermon", "mission"], "theological_category": ["missions"],  "tradition": "Particular Baptist"},
 "BAP-REF-SMITH-VOL01":   {"content_genre": ["commentary"],                 "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL02":   {"content_genre": ["commentary"],                 "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL03":   {"content_genre": ["commentary"],                 "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL04":   {"content_genre": ["commentary"],                 "theological_category": None,             "tradition": None},
}
```

**삽입 규칙 (A-2b-2 EXEC 용):**
- 각 레코드의 `checksum_target:` 줄 다음에 삽입 (현재 마지막 additive 키). 들여쓰기 `  ` 2칸.
- `content_genre` / `theological_category` = YAML flow list: `content_genre: [church_practice, pastoral]`.
- `tradition` = 따옴표 문자열: `tradition: "Particular Baptist"`.
- 값이 `None` 인 필드는 **키를 넣지 않는다**.
- 결과: content_genre 14줄, tradition 10줄, theological_category 5줄 = **총 +29줄, -0**.
- 최종 M2 레코드 키: 13~16개 (base 10 + authority_class + raw_path + checksum_target + [content_genre] + [theological_category] + [tradition]).

---

## 5. 판정 원칙 (규칙 자체에 대한 메타 규칙)

- **결정론적**: 같은 서지 사실 → 같은 값.
- **보수적**: 애매하면 키를 넣지 않는다(WARNING). "일단 채우기" 금지.
- **근거 기록**: §4 표가 서지 근거. A-2b-2 EXEC 은 값 재판단 없이 §4.1 verbatim.
- **vocab 고정**: 값 집합은 §2 를 벗어나지 않는다.
- **불변 아님, 그러나 통제됨**: 개정은 규칙 개정 → 재적용 절차. 임의 수정 금지.
- **M2 전용**: TSU record 에는 쓰지 않는다. 기존 3,319 TSU 무접촉.
- **required 승격 안 함** (OPEN-6 비준): WARNING-first 유지.

---

## 6. OPEN-1~6 — RESOLVED (HQ 2026-08-28, 전부 CUE 권고안대로)

| # | 결정 |
|---|---|
| **OPEN-1** | `theological_category` = 현행 4값 유지. vocab 확장 안 함. 강해·변증·잡문류는 키 생략. |
| **OPEN-2** | 성경사전 `content_genre` = `commentary`. `reference` 값 신설 안 함 (`authority_class=reference` 로 충분). |
| **OPEN-3** | Hiscox `content_genre` = `[church_practice, pastoral]`. Dagg·Hiscox `tradition` = `"Particular Baptist"`. |
| **OPEN-4** | Smith `tradition` = 키 생략 (비침례교 참고 자료). 별도 규약 신설 안 함. |
| **OPEN-5** | 다중 `content_genre` 상한 3, 주형식 우선. Fuller v4 = `[theology]`, v8 = `[theology, sermon, mission]`. |
| **OPEN-6** | 3필드 `required` 승격 안 함. ADR §7.5 WARNING-first 유지. 미결정 소스는 키 생략 허용. |

---

## 7. 다음 절차 (④~⑤)

1. **CUE — A-2b-2 EXEC 명령서 작성**: §4.1 확정표에서 **verbatim** backfill. M2 텍스트 삽입만
   (`yaml.safe_dump` 금지). `content_genre`/`theological_category`/`tradition` 만. 나머지 무접촉.
2. **C1 실행** → validator 갱신(V6 에 content_genre/theological_category vocab enum 검사 추가;
   `tradition` 값 검사) → test 갱신(`test_pos_01/02/03` 를 `_present`/vocab 검사로 FLIP; 신규
   `test_classification_matches_a2b2_v1_1`) → SSOT 갱신(3필드 `populated N/14 (A-2b-2)`).
3. **CUE 독립검증** → 커밋.

---

## 8. 이번 문서가 하지 않는 것

- M2 backfill (값 쓰기) — **하지 않음** (A-2b-2 EXEC 몫).
- 스키마 파일 신규/수정 — 하지 않음.
- validator/test/SSOT 변경 — 하지 않음.

**Mutation: 0. 산출물: 본 문서 (v1.1 RATIFIED).**

END OF A-2b-2 CLASSIFICATION RULE (RATIFIED v1.1)
