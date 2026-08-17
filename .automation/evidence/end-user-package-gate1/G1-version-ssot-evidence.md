# G1 Evidence — Version SSOT 정리

## 변경 사항

### 1. `core/config.py:35` fallback 갱신
- **Before:** `APP_VERSION = _yaml_app.get("version", "0.6.4")`
- **After:** `APP_VERSION = _yaml_app.get("version", "1.3.0")`
- YAML 로드 실패 시 SSOT(`config.yaml::app.version: "1.3.0"`)와 동일한 값으로 안전망 역할

### 2. `dbma_ui.py:1` docstring에서 버전 번호 제거
- **Before:** `"""DBMA v1.1.0 — Production Streamlit Entry Point.`
- **After:** `"""DBMA — Production Streamlit Entry Point.`
- docstring은 코드가 아닌 순수 주석이므로 하드코딩된 버전 숫자 제거

### 3. `scripts/install_nae_beta.command:32` FALLBACK_TAG 갱신
- **Before:** `FALLBACK_TAG="beta-v1.3.0-rc1"`
- **After:** `FALLBACK_TAG="beta-v1.3.0-rc3"`
- 배포 태그 체계이므로 SSOT 대체 아님, 최신 태그로만 갱신

### 4. `pyproject.toml` 무변경 확인
- grep 결과: 버전 관련 줄 없음 — `[project]` version 신규 추가 없음 (Hard Stop 준수)

## SSOT 일관성 검증

| 위치 | 값 | SSOT 일치 여부 |
|------|-----|----------------|
| `config.yaml::app.version` | `"1.3.0"` | **SSOT** |
| `core/config.py:35` fallback | `"1.3.0"` | ✅ 일치 |
| `dbma_ui.py:1` docstring | 버전 번호 제거 | ✅ SSOT 참조(간접) |
| `scripts/install_nae_beta.command:32` FALLBACK_TAG | `"beta-v1.3.0-rc3"` | ✅ 배포 태그(별도 체계) |

## Git status (변경 파일)
```
M core/config.py
M dbma_ui.py
M scripts/install_nae_beta.command
```
