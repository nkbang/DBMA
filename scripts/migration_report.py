"""scripts/migration_report.py — Migration Engine 결과 보고
(NAE-METADATA-MIGRATION-IMPLEMENTATION-001).

authority_validator.py의 ValidationResult와 동일한 PASS/WARNING/FAIL
출력 패턴을 따르되, Migration Engine 고유의 SKIPPED(no-op/Idempotency
결과)를 추가한다.
"""

from __future__ import annotations


class MigrationReport:
    def __init__(self) -> None:
        self.pass_count = 0
        self.warning_count = 0
        self.fail_count = 0
        self.skipped_count = 0
        self.lines: list[str] = []

    def add(self, level: str, message: str) -> None:
        level = level.upper()
        if level == "PASS":
            self.pass_count += 1
        elif level == "WARNING":
            self.warning_count += 1
        elif level == "FAIL":
            self.fail_count += 1
        elif level == "SKIPPED":
            self.skipped_count += 1
        self.lines.append(f"[{level}] {message}")

    def print_all(self) -> None:
        for line in self.lines:
            print(line)
        print()
        print(
            f"=== Migration 결과 요약: PASS={self.pass_count} WARNING={self.warning_count} "
            f"FAIL={self.fail_count} SKIPPED={self.skipped_count} ==="
        )

    @property
    def ok(self) -> bool:
        return self.fail_count == 0
