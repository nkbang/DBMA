# CUE Review Required — NSQ-FAILROUTE-1786776386

- routed_at: 2026-08-15T06:46:26.000Z
- reason: night shift task did not pass evidence verification
- ADR-022 SS8: automation must NOT auto-retry. A human/CUE decision
  is required before this task returns to the queue.

## n8n response
```json
{
  "code": 404,
  "message": "The requested webhook \"POST dbma-automation-phase-e\" is not registered.",
  "hint": "The workflow must be active for a production URL to run successfully. You can activate the workflow using the toggle in the top-right of the editor. Note that unlike test URL calls, production URL calls aren't shown on the canvas (only in the executions list)"
}
```

## Independent verification
- task_file.automation.state=None
- evidence_lines=0 last_to=None
- response.status=None is not a PASS status
