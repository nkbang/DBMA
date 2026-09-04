#!/bin/bash
# ADR-021 Pilot Phase B~D Validation Test Script
# CUE 최종 검증 완료 버전 (2026-08-13) — API 키 불필요 (webhook authentication: none)
# 워크플로우는 task_id로 /automation/tasks/{task_id}.json 파일을 읽는 구조이므로,
# 필드 누락/타입 오류 테스트는 실제 파일을 먼저 만들어야 한다.

set -e

N8N_BASE="http://localhost:5678"
WEBHOOK_PATH="/webhook/dbma-automation-test"
FIXTURE_DIR="/Users/David/DBMA/.automation/tasks/_verify_fixtures"

mkdir -p "$FIXTURE_DIR"

cat > "$FIXTURE_DIR/missing.json" << 'EOF'
{"schema_version":"1.0.0","task_id":"X","title":"t","owner":"C1"}
EOF

cat > "$FIXTURE_DIR/wrongtype.json" << 'EOF'
{"schema_version":"1.0.0","task_id":"X","title":"t","owner":"C1","state":"IDLE","phase":"P","requires_human_approval":false,"production_mutation":"false","evidence":"not_an_array","audit":{"status":null}}
EOF

echo "=== ADR-021 Pilot Phase B~D Validation ==="
echo "n8n URL: $N8N_BASE"
echo "Webhook: $WEBHOOK_PATH"
echo ""

echo "--- Test 1: Valid task (should PASS) ---"
curl -s -X POST "$N8N_BASE$WEBHOOK_PATH" -H "Content-Type: application/json" \
  -d '{"task_id":"ADR-021-PILOT-001"}'
echo -e "\n"

echo "--- Test 2: Missing required fields (should return validation_failed) ---"
curl -s -X POST "$N8N_BASE$WEBHOOK_PATH" -H "Content-Type: application/json" \
  -d '{"task_id":"_verify_fixtures/missing"}'
echo -e "\n"

echo "--- Test 3: Wrong datatype (should return validation_failed) ---"
curl -s -X POST "$N8N_BASE$WEBHOOK_PATH" -H "Content-Type: application/json" \
  -d '{"task_id":"_verify_fixtures/wrongtype"}'
echo -e "\n"

echo "--- Test 4: Non-existent task (should return file_error, NOT empty 200) ---"
curl -s -X POST "$N8N_BASE$WEBHOOK_PATH" -H "Content-Type: application/json" \
  -d '{"task_id":"NONEXISTENT-999"}'
echo -e "\n"

echo "--- Test 5: Malformed JSON body (caught by n8n core body-parser, HTTP 422) ---"
curl -s -w "\nHTTP:%{http_code}\n" -X POST "$N8N_BASE$WEBHOOK_PATH" -H "Content-Type: application/json" \
  -d '{invalid json'
echo ""

rm -rf "$FIXTURE_DIR"
echo "=== All tests completed (fixtures cleaned up) ==="
