# Week 6 - Day 1: Interview Notes: Frontend Integration (React, SSE, Auth, Citations)

## 1. Frontend stack

- React 19 with Vite, React Router, Axios, Tailwind CSS, `react-hook-form`, `react-markdown`, `vitest` for unit tests.
- The API base URL comes from `VITE_API_URL` (set in the Vercel project settings, not committed).
- Streaming uses `fetch()` with a `ReadableStream` reader, not `EventSource`, because `EventSource` cannot send an `Authorization` header or a POST body.

---

## 2. A read-only frontend audit first

Before changing code, an audit compared every backend endpoint with what the frontend calls and listed work as P0 (broken), P1 (missing) and P2 (polish). This avoided blind edits.

Key findings:

- `AuthContext` called `setUser(res.data)` although `res` was already the data, so the user was always `undefined` and the navbar always showed "User".
- The SSE parser called `.trim()` on every token, so spaces disappeared ("Thequickbrownfox").
- No handler for `event: error`; refresh tokens were never stored; a 401 silently killed the session.
- Citations were cut with `.slice(0, 2)`, page numbers and snippets were ignored, there was no role gating, and no way to change roles.
- Calls to deprecated `/users/me`.

---

## 3. SSE parser

Pure function module `utils/sse.js` (unit tested):

- Buffers partial reads and splits events on a blank line (accepts `\n` and `\r\n`).
- Event type from `event:`; for each `data:` line, remove **exactly one** leading space (never trim); join multiple `data:` lines with `\n`.
- Tokens such as `" word"`, `"\n"` or a single character are appended unchanged.
- Handles `metadata` (session id and citations), `token`, `done` and `error`.
- On error: stop loading, keep the text already streamed, show the message inside the assistant bubble with a **Retry** button.

---

## 4. Authentication flow

1. Login or signup stores both `access_token` and `refresh_token`.
2. An Axios response interceptor catches **401**.
3. It calls `POST /auth/refresh` once; all queued requests **share the single in-flight refresh promise**.
4. The original request is retried once with the new token.
5. The interceptor never intercepts `/auth/login` or `/auth/refresh`.
6. If refresh fails, tokens are cleared and the user goes to the login page.

Other interceptor behaviour: 403 shows "You do not have permission", 409 shows the server's detail (for example duplicate document), 503 shows "Service temporarily unavailable".

Security note: tokens are kept in `localStorage`, which is exposed to XSS. A hardened design would use httpOnly cookies. This is a known limitation.

---

## 5. Role-based UI

- A helper `hasRole(user, minRole)` with the order super_admin > admin > manager > employee.
- Upload and delete controls are hidden below MANAGER; the Team page and role dropdown are hidden below ADMIN; routes are guarded too (`ProtectedRoute` with `minRole`).
- Admin users page: a role dropdown per user calls `PUT /users/{id}` with optimistic update and rollback on error.
- This is usability only; the backend enforces the real permissions.

---

## 6. Citation chips

- `[1]`, `[1][2]` and `[ 1 ]` in the final answer become clickable chips (a markdown link transform; no `rehype-raw` and no `dangerouslySetInnerHTML`, to stay safe from XSS).
- A chip opens a popover with document name, page number (hidden when null) and snippet.
- Only sources whose id appears in the text are listed. If the text has no markers and is not the not-found sentence, all returned citations are shown. For the not-found sentence nothing is shown.
- Old sessions loaded from the server render the same way.

---

## 7. Documents dashboard

- Upload progress bar through Axios `onUploadProgress`.
- Loading skeleton on first fetch.
- Status badge and the `error_message` for failed documents.
- Polling `GET /documents` every 3 seconds only while at least one document is `processing`.
- Delete shown only to MANAGER or higher.

---

## 8. Bugs found after the main work

1. **Blank page**: `TypeError: Cannot destructure property 'user' from null or undefined` in `ProtectedRoute`. The auth context was not available where it was read. Fixed, and a top-level **error boundary** was added, so a crash now shows "Something went wrong" with a Reload button instead of a white page. `useAuth` now throws a clear error when used outside the provider.
2. **Add-user crash**: FastAPI's 422 body is `{"detail": [ {type, loc, msg, input, ctx}, ... ]}`, a list of objects. Rendering it directly produced "Objects are not valid as a React child". Fix: a `getErrorMessage(error, fallback)` helper that always returns a string (handles string detail, validation arrays, network errors), used everywhere errors are shown.
3. **Why the 422 happened**: the Add-user form sent a password shorter than 8 characters or a role in the wrong case. The backend contract is: name 2–100 chars, valid email, password 8–100 chars, role exactly `admin`, `manager`, `employee` or `super_admin`. The form now validates the same rules with inline messages and maps 422 field errors to the matching inputs.
4. **Newline tokens**: backend SSE framing was fixed (Week 4 Day 2) and the parser joins multi-line `data:` fields.

Tests: vitest for the SSE parser, the citation marker parser, role checks, and the error helper.

---

## 9. Interview Questions

### Q1. Why use `fetch` for streaming instead of `EventSource`?
`EventSource` cannot set an Authorization header or send a POST body.

### Q2. Why must the SSE parser not trim tokens?
Leading and trailing spaces are part of the generated text; trimming merges words.

### Q3. How does silent token refresh work without a thundering herd?
All concurrent 401 responses wait on a single refresh request, then each retries once.

### Q4. Why hide buttons by role if the backend already checks?
Better user experience. It is not security.

### Q5. How do you render citations safely?
Convert markers to internal links in a markdown component; no raw HTML rendering.

### Q6. What was the cause of the "Objects are not valid as a React child" error?
A FastAPI validation error array was rendered as text.

### Q7. What is an error boundary?
A React component that catches render errors in its children and shows a fallback UI.

### Q8. Where are tokens stored and what is the risk?
In `localStorage`; XSS can read them. httpOnly cookies are safer.

### Q9. Why audit before changing the frontend?
It lists real gaps against the real API and prevents guessing.