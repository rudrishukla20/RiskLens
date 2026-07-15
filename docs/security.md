# RiskLens Security Controls Specification

This document details the security principles, authentication mechanisms, authorization boundaries, and cryptographic controls implemented in the RiskLens Analytics platform.

---

## 1. Authentication & JWT Lifecycle

Authentication is built on JSON Web Tokens (JWT) signed with HMAC-SHA256 (HS256):
- **Access Tokens**: Short-lived (default 60 minutes) containing user identity and roles.
- **Refresh Tokens**: Long-lived (default 7 days) stored in local storage and database.
- **Token Revocation**: Refresh tokens are explicitly deleted from the database on logout, preventing session reuse.

---

## 2. Password Strength Requirements

The system enforces a strict password policy:
- Minimum length of **12 characters**.
- Must contain at least **one uppercase letter**, **one lowercase letter**, **one numeric digit**, and **one special character** (e.g. `!@#$%^&*`).

---

## 3. Role-Based Access Control (RBAC)

Access is strictly segregated by role. 

### Supported Roles
1. **ADMIN**: Full system maintenance capabilities.
2. **CREDIT_RISK_GOVERNANCE_OFFICER (CRGO)**: Read-only access to risk portfolios and metadata.

*Note: No role management API or UI exists to prevent privilege escalation.*

---

## 4. Rate Limiting

The application uses `SlowAPI` to prevent denial-of-service and brute-force attacks:
- **Default limit**: Defined by `RATE_LIMIT_DEFAULT` (e.g. `100/minute`).
- **Auth endpoints**: Strict limits on login and token refresh (e.g. `5/minute`).
- **Upload endpoints**: Restrict large file transfers.

---

## 5. Audit Logging

A centralized audit trail records critical administrative actions. Log entries include:
- Timestamp (UTC)
- Executing user ID
- Action type (e.g. `USER_CREATED`, `DATASET_UPLOADED`)
- Target resource ID & type
- Tracing Request ID
- Contextual metadata (IP address, origin details)
