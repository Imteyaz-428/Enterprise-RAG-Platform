# Week 5 - Day 3: Interview Notes: Security, RBAC, JWT and Multi-Tenancy

## 1. Hierarchical RBAC

Roles in order: **SUPER_ADMIN > ADMIN > MANAGER > EMPLOYEE** ("User" = EMPLOYEE).

A higher role passes any check that requires a lower role.

| Action | Minimum role |
|---|---|
| Chat, list and view documents | any logged-in user |
| Upload and delete documents | MANAGER |
| Create, update, delete users; change roles | ADMIN |
| Act across organizations | SUPER_ADMIN |

All actions are also scoped to the caller's own organization; a mismatch returns 403 with a clear message.

Before this, any employee could delete any document in the organization. The old check compared roles for equality, which ignored MANAGER and EMPLOYEE entirely.

---

## 2. JWT: access and refresh tokens

- **Access token**: short lived (30 minutes), claim `type = "access"`.
- **Refresh token**: 7 days, claim `type = "refresh"`.
- `POST /auth/refresh` exchanges a valid refresh token for a new access token.
- `get_current_user` rejects refresh tokens (401). A refresh token cannot be used to call the API.
- Passwords are hashed with bcrypt.

Startup validation (fail fast): `SECRET_KEY` must be set and at least 32 characters, and `ALGORITHM` must be valid. The app refuses to start otherwise.

---

## 3. Input validation fixes

- `SignupRequest` now enforces the same rules as `UserCreate` and `OrganizationCreate` (password at least 8 characters, slug `^[a-z0-9-]+$`).
- Before, a short password passed the signup schema and then failed when the inner schema was built, producing a **500**. Now bad input returns **422**.

---

## 4. API cleanup

- `/users/login` and `/users/me` are deprecated and hidden from the schema; they delegate to the same code as `/auth/login` and `/auth/me`. They were not deleted because an old frontend might still call them.
- `OAuth2PasswordBearer` points at `/auth/login`.
- Delete endpoints return the same shape: `{"message": "..."}`.

---

## 5. Database integrity (migration 003)

ON DELETE rules:

- `users.organization_id`, `documents.organization_id`, `chat_sessions.organization_id`, `chat_sessions.user_id`, `chat_messages.session_id` → CASCADE
- `documents.uploaded_by` → SET NULL (nullable)

Also: deleting a user does not delete the organization's documents (the ORM cascade on `User.documents` was removed).

---

## 6. Multi-tenancy checklist

- Every table that holds tenant data has `organization_id` (documents and chunks included).
- Retrieval, sessions, users and documents filter by organization.
- Cache keys include the organization id.
- A reusable script `set_role.py` changes roles without touching passwords.
- Tests: 14 organization isolation tests and 10 user isolation tests, plus RBAC matrix tests, refresh-flow tests and cross-organization tests.

---

## 7. Interview Questions

### Q1. What is hierarchical RBAC?
Roles have ranks; a higher role inherits the permissions of lower roles.

### Q2. Why separate access and refresh tokens?
A leaked short-lived access token has limited value, and the long-lived refresh token is used only to obtain new access tokens.

### Q3. Why mark tokens with a `type` claim?
So a refresh token cannot be accepted as an access token.

### Q4. Why validate `SECRET_KEY` at startup?
A weak or missing secret is a security failure; failing at startup is safer than running insecurely.

### Q5. How is tenant isolation enforced?
By `organization_id` on rows, filters in every query, org-scoped cache keys, and dedicated tests.

### Q6. Why return 422 instead of 500 for bad signup data?
It is a client error; 500 suggests a server bug and hides what is wrong.

### Q7. Why keep deprecated routes?
Backward compatibility until all clients migrate.

### Q8. What is the difference between CASCADE and SET NULL?
CASCADE deletes dependent rows; SET NULL keeps them and clears the reference.

### Q9. Is hiding buttons in the UI security?
No. The backend enforces permissions; the UI only improves usability.