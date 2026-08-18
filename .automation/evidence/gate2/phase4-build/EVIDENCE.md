# Phase 4 — Build Validation Evidence

**Date**: 2026-08-18  
**Executor**: C1 (CUE 실시간 감사)  
**Directive**: C1-NIGHT-SHIFT-DIRECTIVE-END-USER-PACKAGE-001.md §3 Phase 4

---

## 1. Build Execution

### Command
```bash
cd ~/DBMA && bash scripts/build_mac_package.sh
```

### Result
```
[1/4] 기존 빌드 정리...
[2/4] .app 번들 구성...
[3/4] 테스터 안내문 작성...
[4/4] .dmg 생성...

완료: /Users/David/DBMA/dist/내서재_베타_설치.dmg
```

---

## 2. Artifact Contents

### .app Bundle (`내서재 베타 설치.app`)
| 파일 | 상태 | 비고 |
|------|------|------|
| `Contents/Info.plist` | ✅ 존재 | CFBundleName=내서재 베타 설치, CFBundleExecutable=launcher |
| `Contents/MacOS/launcher` | ✅ 존재 (248 bytes) | 실행 파일 |
| `Contents/Resources/install_nae_beta.command` | ✅ 존재 | 베타 설치 스크립트 |

### .dmg
| 항목 | 값 |
|------|-----|
| 파일명 | `내서재_베타_설치.dmg` |
| 크기 | 24,966 bytes (28K UDZO) |
| SHA-256 | `58d3fe4bb384f38d50959cc21befd04fd256faaf861cd7863a5c2d305c6c9673` |

---

## 3. Export-Ignore Verification

### .gitattributes
```
NAE/ export-ignore
.automation/ export-ignore
test_seal_*/ export-ignore
```

### git archive 결과 (실제 검증)
| 경로 | git archive 포함 여부 | 상태 |
|------|----------------------|------|
| `NAE/` | ❌ 제외됨 | ✅ GREEN |
| `.automation/` | ❌ 제외됨 | ✅ GREEN |
| `test_seal_*/` | ❌ 제외됨 | ✅ GREEN |

---

## 4. Clean Checkout Reproducibility

### Method
```bash
cd /tmp && rm -rf dbma-gate2-phase4-clean && mkdir dbma-gate2-phase4-clean
git archive HEAD | tar -x -C /tmp/dbma-gate2-phase4-clean
```

### Verification
| 항목 | 결과 |
|------|------|
| `scripts/build_mac_package.sh` 존재 | ✅ GREEN |
| `scripts/setup_beta_tester.command` 존재 | ✅ GREEN |
| `dbma_ui.py` 존재 | ✅ GREEN |
| `NAE/` 제외 | ✅ GREEN |
| `.automation/` 제외 | ✅ GREEN |

---

## 5. Gate Assessment

| 항목 | 결과 |
|------|------|
| .app 번들 생성 | ✅ GREEN |
| .dmg 생성 (UDZO) | ✅ GREEN |
| export-ignore 적용 | ✅ GREEN |
| clean checkout 재현성 | ✅ GREEN |

### **Phase 4 Gate: ALL GREEN**
