# C1 Task Order 063 — INSTALL.md 최소 RAM 사양 값 치환

- 발주: CUE · 일자: 2026-09-15
- 모드: ACT MODE 허용 — 단, 아래 스니펫 1개 파일 1곳만. 다른 파일/다른 줄은
  건드리지 마라.
- 사용 모델: `qwen3.6:35b-DBMAcode-Cline`(코딩용)
- 성격: 단순 값 치환(OLD/NEW 스키마)

## 배경

`scripts/setup_beta_tester.command`는 8GB 미만 Mac에서 설치를 중단시키는데
(`MEM_GB -lt 8`), `INSTALL.md`의 "최소" RAM은 4GB로 적혀 있어 문서와 실제
동작이 불일치한다(`DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md` S1-4, B-5).

## 변경 대상

파일: `INSTALL.md`

**OLD (정확히 이 한 줄만 찾아라):**
```
| RAM | 4 GB | 8 GB+ |
```

**NEW (이걸로 교체):**
```
| RAM | 8 GB | 16 GB+ |
```

## 제약

- 이 한 줄 이외의 `INSTALL.md` 내용(디스크·Python·인터넷 행, 다른 절)은
  절대 건드리지 마라.
- 다른 파일은 열지도 마라.
- 표의 정렬·공백 스타일은 원본 그대로 유지하라(파이프 `|` 위치 변경 금지).

## 완료 보고

변경한 줄의 OLD/NEW를 그대로 다시 출력해 CUE가 diff로 확인할 수 있게
하라. 추가 설명 문단 없이 코드 블록만.
