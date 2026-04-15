# Security Assessment Report

**Source file:** sample.drawio

## Local assessment - severity summary

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 2 |
| Medium | 3 |
| Low | 4 |

## CIS coverage estimates

| Control | Coverage | Safeguards (CIS) |
|---|---|---|
| Data Protection | 60% | 3, 3.1 |
| Account Management | 50% | 5, 5.2 |
| Access Control Management | 40% | 6, 6.1 |
| Audit Log Management | 30% | 8, 8.3 |
| Network Monitoring and Defense | 45% | 13, 13.2 |
| Application Software Security | 55% | 16, 16.4 |

## Threat examples
- SQL injection (Application Software Security)
- Exposed admin interfaces (Account Management)
- Improve input validation (CIS Control 16.4)
- Harden account provisioning (CIS Control 5)

## Notes from the local assessment
- Threat examples:
- CIS notes:
- +

## Raw analysis output
```
Critical: 1
High: 2
Medium: 3
Low: 4

Data Protection coverage: 60% (CIS Control 3, Safeguard 3.1)
Account Management coverage: 50% (CIS Control 5, Safeguard 5.2)
Access Control Management coverage: 40% (CIS Control 6, Safeguard 6.1)
Audit Log Management coverage: 30% (CIS Control 8, Safeguard 8.3)
Network Monitoring and Defense coverage: 45% (CIS Control 13, Safeguard 13.2)
Application Software Security coverage: 55% (CIS Control 16, Safeguard 16.4)

Threat examples:
- SQL injection (Application Software Security)
- Exposed admin interfaces (Account Management)

CIS notes:
- Improve input validation (CIS Control 16.4)
- Harden account provisioning (CIS Control 5)
+
```