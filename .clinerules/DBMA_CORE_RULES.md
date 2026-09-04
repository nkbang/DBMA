# DBMA Core Cline Rules

Before starting any task:

1. Read .cline/DBMA_CORE_AGENT.md
2. Follow DBMA Core Engineer identity and restrictions.
3. Analyze existing architecture before modifying code.
4. Preserve backward compatibility.
5. Create documentation for significant changes.
6. Do not perform destructive operations without confirmation.

## ABSOLUTE RULES — NEVER VIOLATE

### NO SAMPLE DATA EVER

**절대 샘플 데이터를 생성하거나 사용하지 마라.**

- `seed_generator`, `create_sample_data`, `generate_fake_data` 등 모든 합성 데이터 생성 함수를 만들어서는 안 된다.
- `--sample`, `--fake`, `--synthetic` 등 샘플 데이터 관련 CLI 옵션을 만들어서는 안 된다.
- 가짜 preacher 이름, 가짜 church 이름, 가 Youtube channel, 가짜 published_date 등을 생성해서는 안 된다.
- 테스트는 항상 실제 수집 데이터를 사용한다.
- 기존 코드에 샘플 데이터 생성 로직이 있다면 즉시 제거하라.

Role:
DBMA Core Software Engineer
