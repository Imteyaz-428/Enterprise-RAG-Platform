# Week 1 - Day 6: Authentication & Authorization

---

## Q1. What is Authentication?

**Answer**

Authentication is the process of verifying **who the user is**.

The user provides credentials (such as email and password), and the system verifies them before granting access.

Example:

```text
Email + Password
        │
        ▼
Verify Credentials
        │
        ▼
Authenticated User
```

---

## Q2. What is Authorization?

**Answer**

Authorization determines **what an authenticated user is allowed to do**.

Example:

```text
Admin
├── Create Organization
├── Delete Users
└── Upload Documents

Employee
├── Upload Documents
└── Ask Questions
```

A user must first be authenticated before authorization is checked.

---

### Follow-up Question

**Authentication vs Authorization?**

| Authentication | Authorization |
|----------------|---------------|
| Verifies identity | Verifies permissions |
| Happens first | Happens after authentication |
| Login | Access Control |

---

## Q3. What is JWT?

**Answer**

JWT (JSON Web Token) is a secure, stateless authentication mechanism.

After successful login, the server generates a signed token and sends it to the client.

The client sends this token with every protected request.

The server verifies the token before allowing access.

---

## Q4. Why is JWT called Stateless?

**Answer**

JWT is called stateless because the server does **not** store session information.

Every request contains all the information required to authenticate the user.

The server only verifies the token signature.

Benefits:

- Better scalability
- Easier deployment
- No server-side session storage

---

### Follow-up Question

**Session Authentication vs JWT Authentication?**

| Session Authentication | JWT Authentication |
|------------------------|-------------------|
| Server stores sessions | No session storage |
| Stateful | Stateless |
| More memory usage | Less memory usage |
| Better for traditional web apps | Better for APIs & Microservices |

---

## Q5. Explain the JWT Authentication Flow.

**Answer**

```text
User Login
      │
      ▼
Verify Email & Password
      │
      ▼
Generate JWT Token
      │
      ▼
Return Token to Client
      │
      ▼
Client stores Token
      │
      ▼
Client sends Token in Authorization Header
      │
      ▼
Server verifies Token
      │
      ▼
Access Granted
```

---

## Q6. Why do we use OAuth2PasswordBearer?

**Answer**

`OAuth2PasswordBearer` extracts the JWT token from the Authorization header.

Example:

```http
Authorization: Bearer <JWT_TOKEN>
```

FastAPI automatically retrieves the token so we don't have to parse headers manually.

---

## Q7. What is `get_current_user()`?

**Answer**

`get_current_user()` is a dependency that:

1. Extracts the JWT token.
2. Verifies the token.
3. Decodes the payload.
4. Retrieves the corresponding user from the database.
5. Returns the authenticated user object.

This dependency protects all secure routes.

---

## Q8. What is RBAC (Role-Based Access Control)?

**Answer**

RBAC restricts access based on user roles.

Example:

```text
Admin
├── Create Organization
├── Manage Users
└── Upload Documents

Employee
├── Upload Documents
└── Search Documents
```

Each role has predefined permissions.

---

### Follow-up Question

**Why use RBAC instead of checking usernames?**

**Answer**

Permissions should depend on roles, not individual users.

This makes the system:

- Easier to manage
- More scalable
- More secure

---

## Q9. Why do we use Dependencies for authentication?

**Answer**

Dependencies make authentication reusable.

Instead of writing authentication logic in every route, we write it once and reuse it everywhere.

Example:

```python
current_user: User = Depends(get_current_user)
```

Benefits:

- Cleaner code
- Better maintainability
- Code reuse

---

## Revision Summary

- Authentication
- Authorization
- JWT
- Stateless Authentication
- JWT Flow
- OAuth2PasswordBearer
- Current User Dependency
- RBAC
- FastAPI Dependencies