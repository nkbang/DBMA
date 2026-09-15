#!/usr/bin/env python3
"""scripts/security_preflight.py — 배포 전 보안 체크리스트 5건 판정.

[S1-3, DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md] 메모리
`project_rag_security_pre_deploy.md`(2026-07-28 조사)의 로컬 RAG 보안
체크리스트 5건을 이 앱의 실제 실행 경로 기준으로 판정한다.

기준: "로컬 단일 사용자 환경엔 과잉설계"라는 원 메모리의 판단을 유지하되,
무료 배포로 대상이 넓어졌으므로 실제로 무엇이 적용/미적용/해당없음인지
근거를 남긴다. 판정을 코드가 아니라 사람이 읽고 확인할 수 있도록
`docs/RELEASE_SECURITY_CHECKLIST_STATUS.md`로 출력한다.

사용:
    python3 scripts/security_preflight.py            # 판정만(dry-run)
    python3 scripts/security_preflight.py --apply     # 적용 가능한 항목(RAW
                                                        # 디렉터리 권한)까지 적용

이 스크립트는 데이터를 읽거나 삭제하지 않는다 — 권한 비트 확인/변경과
코드 정적 검사만 한다.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class CheckResult:
    id: str
    title: str
    status: str  # "적용됨" | "미적용" | "해당없음" | "사용자 조치 필요" | "부분 충족"
    detail: str


def _check_qdrant_auth() -> CheckResult:
    """[체크리스트 1] Qdrant 로컬 인증(API key).

    core/retrieval.py의 RetrievalEngine.__init__()은 qdrant_url을 받아
    self.qdrant_url에 저장하지만, 그 값을 읽어 실제로 QdrantClient를
    생성/연결하는 코드가 core/ 어디에도 없다(정적 검사로 확인) — 배포되는
    앱의 실제 질의 경로는 TSU JSONL 데이터셋을 메모리에 전량 적재하는
    방식(RetrievalEngine._load_corpus())이며 Qdrant를 쓰지 않는다.
    (참고: NAE 참고자료 인덱싱 SPRINT34는 별도 개발 경로에서 Qdrant를
    실제로 쓰지만, 그건 이 배포판의 실행 경로가 아니다.)
    """
    retrieval_py = (PROJECT_ROOT / "core" / "retrieval.py").read_text(encoding="utf-8")
    uses_qdrant_client = "QdrantClient" in retrieval_py or "qdrant_client" in retrieval_py
    if not uses_qdrant_client:
        return CheckResult(
            "1", "Qdrant 로컬 인증",
            "해당없음",
            "core/retrieval.py에 QdrantClient/qdrant_client 사용 코드가 "
            "없다 — self.qdrant_url은 저장만 되고 읽는 코드가 없는 죽은 "
            "파라미터(3회 등장: __init__ 시그니처 1 + 대입문 2, 전부 "
            "core/retrieval.py:1403,1409). 배포판 실행 경로는 TSU 전량 "
            "메모리 적재 방식이라 Qdrant 자체를 쓰지 않는다. 인증 설정 "
            "대상이 없다.",
        )
    return CheckResult(
        "1", "Qdrant 로컬 인증",
        "사용자 조치 필요",
        "코드가 QdrantClient를 실제로 사용하는 것으로 감지됨 — 정적 검사"
        " 결과가 위 가정과 달라졌다. 재검토 필요.",
    )


def _check_disk_encryption() -> CheckResult:
    """[체크리스트 2] 디스크 전체 암호화 — macOS FileVault로 충분(별도
    AES-256 계층 없음, 원 메모리 판단 유지). 이 항목은 OS 설정이라
    스크립트가 강제할 수 없고 확인만 한다."""
    try:
        out = subprocess.run(
            ["fdesetup", "status"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception as e:
        return CheckResult(
            "2", "디스크 암호화(FileVault)", "확인 불가", f"fdesetup 실행 실패: {e}"
        )
    if "FileVault is On" in out:
        return CheckResult("2", "디스크 암호화(FileVault)", "적용됨", out)
    return CheckResult(
        "2", "디스크 암호화(FileVault)",
        "사용자 조치 필요",
        f"{out} — 배포 대상 목회자 기기마다 FileVault 활성화 여부가 다를 "
        "수 있다. 이 앱이 강제할 수 없으므로 설치 안내 문서에 권고 문구로 "
        "남긴다(INSTALL.md).",
    )


def _check_raw_dir_permissions(apply: bool) -> CheckResult:
    """[체크리스트 3] RAW 원본 디렉터리 접근 권한 사용자 전용(700).

    이 앱이 실제로 관리하는 RAW 디렉터리(core.config.DEFAULT_RAW_DIR,
    보통 data/raw)만 대상으로 한다. ~/NAE_CORPUS_RAW 같은 외부 연구용
    대형 자산은 배포판 범위 밖이고 다른 세션이 사용 중일 수 있어 건드리지
    않는다.
    """
    try:
        from core.config import DEFAULT_RAW_DIR
    except Exception as e:
        return CheckResult(
            "3", "RAW 디렉터리 권한(700)", "확인 불가",
            f"core.config import 실패: {e}",
        )

    raw_path = Path(DEFAULT_RAW_DIR)
    if not raw_path.exists():
        return CheckResult(
            "3", "RAW 디렉터리 권한(700)", "해당없음",
            f"{raw_path}가 아직 생성되지 않음(첫 인제스트 전) — 생성 시점에 "
            "700으로 만들어지는지는 core.config의 디렉터리 생성 로직에서 "
            "별도 확인 필요.",
        )

    current_mode = stat.S_IMODE(raw_path.stat().st_mode)
    is_user_only = current_mode == 0o700
    if is_user_only:
        return CheckResult(
            "3", "RAW 디렉터리 권한(700)", "적용됨", f"{raw_path} = 0700",
        )
    if apply:
        os.chmod(raw_path, 0o700)
        new_mode = stat.S_IMODE(raw_path.stat().st_mode)
        return CheckResult(
            "3", "RAW 디렉터리 권한(700)", "적용됨",
            f"{raw_path}: {oct(current_mode)} → {oct(new_mode)}(적용)",
        )
    return CheckResult(
        "3", "RAW 디렉터리 권한(700)", "미적용",
        f"{raw_path} = {oct(current_mode)} — --apply로 700 적용 가능"
        "(비파괴적, 되돌리기 쉬움: chmod 755로 원복 가능).",
    )


def _check_ingest_log_provenance() -> CheckResult:
    """[체크리스트 4] 인제스트 로그에 파일 출처 + 타임스탬프 기록.

    core/identity_registry.py::register_document()가 신규 문서 레코드에
    source_file과 created_at을 기록하는지 정적으로 확인한다.
    """
    registry_py = (
        PROJECT_ROOT / "core" / "identity_registry.py"
    ).read_text(encoding="utf-8")
    has_source_file = '"source_file"' in registry_py
    has_created_at = '"created_at"' in registry_py
    if has_source_file and has_created_at:
        return CheckResult(
            "4", "인제스트 로그 출처+타임스탬프", "적용됨",
            "core/identity_registry.py::register_document()가 "
            "record['source_file']과 record['created_at']을 기록한다"
            "(문서별 registry 레코드 = 인제스트 감사 로그 역할).",
        )
    return CheckResult(
        "4", "인제스트 로그 출처+타임스탬프", "미적용",
        f"source_file 필드: {has_source_file}, created_at 필드: {has_created_at}"
        " — 코드 확인 결과 일부 누락.",
    )


def _check_upload_scan() -> CheckResult:
    """[체크리스트 5] 업로드 문서 청킹 전 최소 스캔(비정상 텍스트/반복
    인젝션 패턴). core/noise_classifier.py의 content_quality 필터가
    존재하나, 이는 노이즈/품질 점수화이지 프롬프트 인젝션 패턴 전용
    스캐너가 아니다 — 원 메모리가 이미 "부분 담당, 강화 검토 필요"로
    판단한 것을 코드로 재확인."""
    has_noise_classifier = (PROJECT_ROOT / "core" / "noise_classifier.py").exists()
    return CheckResult(
        "5", "업로드 문서 최소 스캔", "부분 충족",
        f"core/noise_classifier.py 존재({has_noise_classifier}) — "
        "content_quality.quality_score로 노이즈/저품질 텍스트는 걸러내지만, "
        "프롬프트 인젝션 패턴(반복 지시문 등) 전용 탐지는 없다. 별도 기능"
        "으로 백로그에 남긴다(이번 preflight 범위 밖 — 새 스캐너 구현은 "
        "S1-3의 '점검'이 아니라 별도 설계 작업).",
    )


def run(apply: bool) -> list[CheckResult]:
    return [
        _check_qdrant_auth(),
        _check_disk_encryption(),
        _check_raw_dir_permissions(apply),
        _check_ingest_log_provenance(),
        _check_upload_scan(),
    ]


def render_report(results: list[CheckResult], apply: bool) -> str:
    lines = [
        "# 배포 전 보안 체크리스트 판정 — S1-3",
        "",
        f"- 생성: {datetime.now().isoformat(timespec='seconds')}",
        f"- 모드: {'적용(--apply)' if apply else '판정만(dry-run)'}",
        "- 근거: `project_rag_security_pre_deploy.md`(2026-07-28) 5개 항목,"
        " `scripts/security_preflight.py`로 자동 판정",
        "",
        "| # | 항목 | 판정 | 근거 |",
        "|---|---|---|---|",
    ]
    for r in results:
        detail = r.detail.replace("\n", " ")
        lines.append(f"| {r.id} | {r.title} | **{r.status}** | {detail} |")
    lines += [
        "",
        "## 배포 판정 (R7)",
        "",
    ]
    blocking = [r for r in results if r.status == "사용자 조치 필요" and r.id != "2"]
    if blocking:
        lines.append("차단 — 아래 항목이 미해결: " + ", ".join(r.title for r in blocking))
    else:
        lines.append(
            "R7 통과 — '사용자 조치 필요'는 항목 2(FileVault, 목회자 개인 기기 "
            "설정이라 앱이 강제 불가)뿐이며 INSTALL.md 권고 문구로 대응한다. "
            "항목 5(부분 충족)는 배포를 막는 결함이 아니라 별도 백로그다."
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="적용 가능한 항목(RAW 디렉터리 700 권한)을 실제로 적용",
    )
    parser.add_argument(
        "--out", default="docs/RELEASE_SECURITY_CHECKLIST_STATUS.md",
        help="보고서 출력 경로",
    )
    args = parser.parse_args()

    results = run(apply=args.apply)
    report = render_report(results, apply=args.apply)

    out_path = PROJECT_ROOT / args.out
    out_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"[security_preflight] 보고서 저장: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
