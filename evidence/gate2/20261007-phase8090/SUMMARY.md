# Gate 2 Phase 80/90 평가

- run: 20261007-phase8090 (이전 run 20261007-224149의 N/A 정정 보강)
- 기준 HEAD: cb234fd779850f6f786c695861c5495dd0fd722f
- Phase 80 (reinstall/upgrade): **PASS** — PERSIST_ITEMS 8/8 보존·내용 일치, lost 0
- Phase 90 (uninstall/cleanup): **PASS** — 지정 /tmp 디렉터리 삭제, 잔여물 없음, 추적 파일 변경 없음
- 이전 N/A 판정은 스크립트 경로 조회 오류였으며 본 run이 정정

## 한계 (확대 해석 금지)
- 80은 install_nae_beta.command 로직의 /tmp 시뮬레이션이다. 실제 설치 스크립트 end-to-end 검증이 아니다.
- 시딩 데이터는 git archive HEAD 기반 마커이며 실제 사용자 데이터가 아니다.
- 실제 설치 경로 ~/내서재_베타는 이 기기에 없어 접촉하지 않았다.
- 스크립트 결함 D1~D3은 80_90_findings.json에 기록(수정하지 않음).
- 90_real_output.txt는 대화 기록에서 복원한 최초 출력이다(원본 캡처 파일은 재실행으로 덮어써짐). 재실행 출력은 90_rerun_idempotent_output.txt.
- 실행 주체: 사용자 터미널(자동 분류기가 CUE의 non-dry-run 실행을 거부함).

## Payload
manifest.json 참조(자기 해시는 manifest에만 기재).
