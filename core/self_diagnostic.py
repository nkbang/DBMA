"""core/self_diagnostic.py — 앱 내 자가 진단 (S5-3).

DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md S5-3. 목회자 테스터가 "화면이
이상하다"고 문의할 때, David가 원격으로 로그를 들여다보지 않아도 사용자
자신이 눌러서 상태를 확인할 수 있는 5개 항목 — Ollama 연결, 필수 모델
존재, 디스크 여유, 성경 본문 등록 여부, 코퍼스 건수.

`scripts/security_preflight.py`의 CheckResult 패턴을 재사용한다 — 이
모듈은 그 스크립트를 import하지 않는다(하나는 배포 전 개발자용 CLI,
하나는 앱 내 런타임용 함수라 성격이 다르다). 이 모듈은 순수 함수만
제공하고 Streamlit을 import하지 않는다 — UI는 ui/pages/help.py가 담당.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from core.config import (
    DEFAULT_EMBED_MODEL,
    DEFAULT_GEN_MODEL,
    DEFAULT_TSU_DATASET_PATH,
)

_MIN_FREE_DISK_GB = 2  # 여유 공간 경고 임계값 — INSTALL.md 최소 5GB보다 보수적으로 낮게 잡아 "곧 부족해질 것"만 경고


@dataclass
class DiagnosticResult:
    id: str
    title: str
    status: str  # "정상" | "확인 필요" | "오류"
    detail: str


def _check_ollama_connection() -> DiagnosticResult:
    try:
        import ollama
        ollama.list()
    except Exception as e:
        return DiagnosticResult(
            "ollama", "Ollama 연결", "오류",
            f"Ollama에 연결할 수 없습니다 — 실행 중인지 확인하세요. ({e})",
        )
    return DiagnosticResult("ollama", "Ollama 연결", "정상", "Ollama가 응답합니다.")


def _check_required_models() -> DiagnosticResult:
    try:
        import ollama
        # ollama.list()는 dict가 아니라 ListResponse 객체를 반환한다 —
        # .models가 Model 객체 리스트이고, 이름은 .model 속성에 있다
        # (실측 확인: ollama 0.34.x).
        installed = {m.model for m in ollama.list().models if m.model}
    except Exception as e:
        return DiagnosticResult(
            "models", "필수 모델", "확인 필요",
            f"Ollama에 연결할 수 없어 모델 목록을 확인하지 못했습니다. ({e})",
        )

    required = {DEFAULT_EMBED_MODEL, DEFAULT_GEN_MODEL}
    # ollama.list()의 model 이름은 태그가 없어도 ":latest"가 붙을 수 있어
    # 느슨하게(접두사) 비교한다.
    missing = [
        m for m in required
        if not any(installed_name and installed_name.startswith(m.split(":")[0]) for installed_name in installed)
    ]
    if missing:
        return DiagnosticResult(
            "models", "필수 모델", "오류",
            f"다음 모델이 없습니다: {', '.join(missing)}. 설치 프로그램을 다시 실행해 주세요.",
        )
    return DiagnosticResult(
        "models", "필수 모델", "정상",
        f"임베딩({DEFAULT_EMBED_MODEL})·생성({DEFAULT_GEN_MODEL}) 모델 모두 확인됨.",
    )


def _check_disk_space() -> DiagnosticResult:
    try:
        usage = shutil.disk_usage(str(Path.cwd()))
    except Exception as e:
        return DiagnosticResult("disk", "디스크 여유 공간", "확인 필요", f"확인 실패: {e}")
    free_gb = usage.free / (1024 ** 3)
    if free_gb < _MIN_FREE_DISK_GB:
        return DiagnosticResult(
            "disk", "디스크 여유 공간", "오류",
            f"여유 공간이 {free_gb:.1f}GB뿐입니다 — 자료 처리가 실패할 수 있습니다.",
        )
    return DiagnosticResult("disk", "디스크 여유 공간", "정상", f"{free_gb:.1f}GB 여유 있음.")


def _check_bible_text() -> DiagnosticResult:
    try:
        from core.bible_text import load_bible_text
        bible = load_bible_text()
    except Exception as e:
        return DiagnosticResult("bible", "성경 본문", "확인 필요", f"확인 실패: {e}")
    if not bible.available:
        return DiagnosticResult(
            "bible", "성경 본문", "확인 필요",
            "성경 본문이 등록되지 않았습니다 — 「본문 해설」 화면에서 절 본문을 볼 수 없습니다. "
            "INSTALL.md '성경 본문 추가하기' 참고(다른 기능은 정상 동작).",
        )
    return DiagnosticResult(
        "bible", "성경 본문", "정상", f"{bible.version_label} 등록됨, {len(bible.list_books())}권.",
    )


def _check_corpus_size() -> DiagnosticResult:
    tsu_path = Path(DEFAULT_TSU_DATASET_PATH)
    if not tsu_path.exists():
        return DiagnosticResult(
            "corpus", "자료 코퍼스", "확인 필요",
            "처리된 자료가 아직 없습니다 — 「자료 등록」에서 자료를 추가해 주세요.",
        )
    try:
        with open(tsu_path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
    except OSError as e:
        return DiagnosticResult("corpus", "자료 코퍼스", "확인 필요", f"확인 실패: {e}")
    if count == 0:
        return DiagnosticResult(
            "corpus", "자료 코퍼스", "확인 필요",
            "처리된 자료가 0건입니다 — 검색·설교 준비 기능이 근거를 찾지 못합니다.",
        )
    return DiagnosticResult("corpus", "자료 코퍼스", "정상", f"{count:,}개 자료 조각 확인됨.")


def run_self_diagnostic() -> list[DiagnosticResult]:
    """5개 항목을 순서대로 점검해 반환한다. 항목 하나가 예외를 던져도
    나머지 점검은 계속된다(fail-closed 아님 — 진단 도구 자체가 죽으면
    안 된다)."""
    checks = [
        _check_ollama_connection,
        _check_required_models,
        _check_disk_space,
        _check_bible_text,
        _check_corpus_size,
    ]
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            results.append(DiagnosticResult(check.__name__, check.__name__, "오류", f"진단 중 예외: {e}"))
    return results
