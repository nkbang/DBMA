# DBMA Automation Production Rules

## Agent Authority

C1:
- implementation
- testing
- debugging
- refactoring
- prototyping

CUE:
- architecture
- governance
- ADR authority
- independent verification
- production integrity
- approval gate

## Mandatory Workflow

C1 Build
→ CUE Audit
→ C1 Correct
→ CUE Re-audit
→ CUE Approve

## Production Rules

1. n8n MUST NOT mutate Production data.
2. n8n MUST NOT approve Governance changes.
3. n8n MUST NOT authorize Full Processing.
4. n8n MUST NOT bypass CUE audit.
5. Human approval MUST remain available for governance-sensitive actions.
6. Every state transition MUST be logged.
7. Every audit result MUST reference evidence.
8. Failed validation MUST stop downstream automation.
9. Production integrity MUST be independently verified.
10. Pilot PASS does NOT authorize Full Processing.
