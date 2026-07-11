# Week 1 - Day 5: User Module

---

## Q1. Why do we hash passwords instead of encrypting them?

**Answer**

Passwords should never be recoverable.

Hashing is a **one-way process**, meaning the original password cannot be obtained from the hash.

Encryption is reversible, which makes it unsuitable for password storage.

Therefore, passwords should always be hashed.

---

### Follow-up Question

**What is the difference between Hashing and Encryption?**

**Answer**

**Hashing**
- One-way process.
- Cannot recover the original password.
- Used for password storage.

**Encryption**
- Two-way process.
- Data can be decrypted using a key.
- Used for confidential information.

---

## Q2. Why did you choose bcrypt?

**Answer**

bcrypt is specifically designed for password hashing.

Advantages:

- Automatically generates a unique salt.
- Resistant to brute-force attacks.
- Slow hashing algorithm, making attacks more difficult.

---

## Q3. Explain the password hashing workflow.

**Answer**

### Registration

```text
Plain Password

↓

bcrypt Hash

↓

Store Hash in Database
```

### Login

```text
User Password

↓

bcrypt Hash

↓

Compare with Stored Hash

↓

Login Success / Failure
```

The original password is never stored.

---

## Q4. Why do we never compare plain passwords?

**Answer**

The database stores only hashed passwords.

During login, the entered password is hashed again.

The two hashes are compared.

Plain text passwords are never stored or compared.

---

## Q5. Why is Email unique?

**Answer**

Email uniquely identifies a user.

Benefits:

- Prevents duplicate accounts.
- Simplifies login.
- Maintains data integrity.

This is enforced using a **Unique Constraint** in PostgreSQL.

---

## Q6. Why do we use Pydantic Validation?

**Answer**

Pydantic validates user input before it reaches the business logic.

Examples:

- Valid email format.
- Minimum password length.
- Required fields.
- Allowed enum values.

Invalid requests are rejected automatically.

---

### Follow-up Question

**Why validate data before inserting into the database?**

**Answer**

Validation prevents:

- Invalid records.
- Unexpected errors.
- Security vulnerabilities.
- Unnecessary database operations.

---

## Q7. What is the purpose of `model_dump(exclude_unset=True)`?

**Answer**

When updating a user, only the provided fields should change.

Example:

```json
{
    "name": "Imteyaz"
}
```

Without `exclude_unset=True`, missing fields could overwrite existing values.

Using `exclude_unset=True` updates only the supplied fields.

---

## Q8. How did you handle duplicate emails?

**Answer**

The database enforces email uniqueness.

If a duplicate email is inserted:

- PostgreSQL raises an IntegrityError.
- The application catches the exception.
- A meaningful HTTP response is returned.

This improves user experience.

---

## Revision Summary

- Password Hashing
- Hashing vs Encryption
- bcrypt
- Password Verification
- Unique Constraints
- Pydantic Validation
- Partial Updates
- IntegrityError Handling