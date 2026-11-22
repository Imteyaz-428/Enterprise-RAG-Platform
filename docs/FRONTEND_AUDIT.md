# 🔍 Frontend Audit: Enterprise RAG Platform

**Audit Date**: November 2026  
**Target Scope**: `frontend/` (package.json, src/**) vs. Backend API (`backend/router/*.py`, `backend/schemas/*.py`, `backend/app.py`, `README.md`)  
**Status**: READ-ONLY Audit Report  

---

## 1. Frontend Technology Stack & Build Configuration

| Component | Technology | Version | Purpose / Configuration |
| :--- | :--- | :--- | :--- |
| **Framework** | React | `^19.2.7` | UI component tree with React 19 JSX runtime |
| **Build Tool** | Vite | `^8.1.1` | Build pipeline using `@vitejs/plugin-react` (`^6.0.3`) |
| **Routing** | React Router DOM | `^7.18.1` | Client-side routing (`<Routes>`, `<Route>`, `<Navigate>`) |
| **State Management** | React Context API | Native | `AuthContext` (`frontend/src/context/AuthContext.jsx`) + local React hooks (`useState`, `useMemo`, `useRef`). Form state managed via `react-hook-form` (`^7.82.0`). |
| **HTTP Client** | Axios | `^1.18.1` | Configured instance in `frontend/src/services/api.js` for REST endpoints |
| **Streaming Client** | Fetch API + ReadableStream | Native Browser | Implemented in `frontend/src/services/chat.js` using `fetch()` and `getReader()` with `TextDecoder` (needed because standard browser `EventSource` cannot send custom `Authorization: Bearer <token>` headers or execute `POST` requests) |
| **Styling** | Tailwind CSS | `^4.3.3` | Tailwind v4 using `@tailwindcss/vite` (`^4.3.3`) and `@tailwindcss/typography` (`^0.5.20`) |
| **Icons & Notifications** | Lucide React & React Hot Toast | `^1.26.0` / `^2.6.0` | UI icons and feedback notifications |
| **Markdown Rendering** | React Markdown + remark-gfm | `^10.1.0` / `^4.0.1` | Markdown formatting for LLM streaming responses in chat bubbles |

### Environment Variables & API Base URL Configuration
- **Configuration File**: `frontend/.env` (and environment overrides during deployment).
- **Environment Variable**: `VITE_API_URL`
- **Current Value in `.env`**: `https://enterprise-rag-platform-mu5i.onrender.com`
- **Application Consumption**:
  - `frontend/src/services/api.js` (line 5): `baseURL: import.meta.env.VITE_API_URL`
  - `frontend/src/services/chat.js` (line 4): `const BASE_URL = import.meta.env.VITE_API_URL;`
- **Observation / Risk**: Neither file specifies a fallback URL (e.g., `import.meta.env.VITE_API_URL || "http://localhost:8000"`). If `VITE_API_URL` is omitted in an environment, Axios defaults to origin while `fetch()` makes requests to `undefined/chat/stream`.

### Build & Dev Commands
- **Local Development**: `npm run dev` (executes `vite`)
- **Production Build**: `npm run build` (executes `vite build`)
- **Code Linting**: `npm run lint` (executes `eslint .`)
- **Build Preview**: `npm run preview` (executes `vite preview`)

---

## 2. Backend Endpoint Inventory & Frontend Consumption

The table below catalogs every endpoint registered across `backend/app.py` and `backend/router/*.py`, the minimum required role per the RBAC hierarchy (`SUPER_ADMIN` > `ADMIN` > `MANAGER` > `EMPLOYEE`), and whether/where the frontend calls it.

| Router | Method | Path | Minimum Role | Frontend Called? | Frontend Caller (File & Function) |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Auth** | `POST` | `/auth/signup` | Public | **Yes** | `frontend/src/services/auth.js:signup()` |
| **Auth** | `POST` | `/auth/login` | Public | **Yes** | `frontend/src/services/auth.js:login()` |
| **Auth** | `POST` | `/auth/refresh` | Public / Refresh Token | **No** | *Missing* (No silent refresh implemented) |
| **Auth** | `GET` | `/auth/me` | Employee | **No** | *Missing* (Frontend calls deprecated `/users/me`) |
| **Users** | `POST` | `/users/` | Admin | **Yes** | `frontend/src/services/user.js:createUser()` |
| **Users** | `GET` | `/users/` | Admin | **Yes** | `frontend/src/services/user.js:getUsers()` |
| **Users** | `PUT` | `/users/change-password` | Employee | **Yes** | `frontend/src/services/user.js:changePassword()` |
| **Users** | `PUT` | `/users/{user_id}` | Employee (Self) / Admin | **Partial** | `frontend/src/services/user.js:updateUser()` (called in `ProfileCard.jsx:handleSave` for self, never called in `Users.jsx` for role changes) |
| **Users** | `DELETE` | `/users/{user_id}` | Admin | **Yes** | `frontend/src/services/user.js:deleteUser()` |
| **Users** | `GET` | `/users/{user_id}` | Employee (Org-scoped) | **No** | *Unused* |
| **Users** | `POST` | `/users/login` | Public | **No** | *Deprecated route in backend; frontend uses `/auth/login`* |
| **Users** | `GET` | `/users/me` | Employee | **Yes** *(Deprecated)* | `frontend/src/services/auth.js:me()`, `frontend/src/services/user.js:getCurrentUser()` |
| **Documents** | `POST` | `/documents/upload` | Manager | **Yes** | `frontend/src/services/document.js:uploadDocument()` |
| **Documents** | `GET` | `/documents` | Employee | **Yes** | `frontend/src/services/document.js:getDocuments()` |
| **Documents** | `GET` | `/documents/{document_id}` | Employee | **No** | *Unused* |
| **Documents** | `DELETE` | `/documents/{document_id}` | Manager | **Yes** | `frontend/src/services/document.js:deleteDocument()` |
| **Chat** | `POST` | `/chat` | Employee | **No** | *Unused* (Frontend exclusively uses streaming endpoint) |
| **Chat** | `POST` | `/chat/stream` | Employee | **Yes** | `frontend/src/services/chat.js:streamChat()` |
| **Chat** | `GET` | `/chat/providers/health` | Employee | **No** | *Unused* |
| **Chat** | `GET` | `/chat/sessions` | Employee | **Yes** | `frontend/src/services/chat.js:getSessions()` |
| **Chat** | `GET` | `/chat/sessions/{session_id}` | Employee | **Yes** | `frontend/src/services/chat.js:getSession()` |
| **Chat** | `DELETE` | `/chat/sessions/{session_id}` | Employee | **Yes** | `frontend/src/services/chat.js:deleteSession()` |
| **Organizations** | `POST` | `/organizations/` | Super Admin | **No** | *Unused* (Org creation is handled via `/auth/signup`) |
| **Organizations** | `GET` | `/organizations/` | Admin | **No** | *Unused* |
| **Organizations** | `GET` | `/organizations/{organization_id}` | Admin | **No** | *Unused* |
| **Organizations** | `PUT` | `/organizations/{organization_id}` | Admin | **No** | *Unused* |
| **Organizations** | `DELETE` | `/organizations/{organization_id}` | Admin | **No** | *Unused* |
| **App Core** | `GET` | `/` | Public | **No** | *Root health check* |
| **App Core** | `GET` | `/health` | Public | **No** | *Container liveness probe* |
| **App Core** | `GET` | `/health/ready` | Public | **No** | *Container readiness probe* |

---

## 3. Feature-by-Feature Gap Analysis

| Feature | Status | File References | Detailed Finding |
| :--- | :---: | :--- | :--- |
| **Login & Registration (Org Creation)** | **Partial** | `pages/Login/Login.jsx`<br>`pages/Signup/Signup.jsx`<br>`services/auth.js` | Form submissions call `/auth/login` and `/auth/signup` correctly. However, `Signup.jsx` (line 32) navigates users back to `/` (login) instead of `/dashboard` after successfully creating the workspace and receiving access tokens. Only `access_token` is stored; `refresh_token` returned by the backend is discarded. |
| **Token Storage & Silent Refresh via `POST /auth/refresh`** | **Missing** | `utils/token.js`<br>`services/api.js`<br>`context/AuthContext.jsx` | `token.js` only provides getters/setters for `access_token`. `refresh_token` is never persisted. `POST /auth/refresh` is never called. There is no Axios response interceptor to intercept 401 errors, attempt token renewal, or trigger a clean logout if refresh fails. When the 30-minute access token expires, API requests simply fail. |
| **Document Dashboard (Status, Error, Delete, Roles)** | **Partial** | `pages/Documents/Documents.jsx`<br>`components/document/DocumentRow.jsx`<br>`components/upload/Upload.jsx`<br>`components/layout/Sidebar.jsx` | 1. **Upload Progress**: **Missing**. Files are uploaded sequentially with an indeterminate spinner; no progress bar or Axios `onUploadProgress` callback.<br>2. **Error Message**: **Missing**. `DocumentRow.jsx` only inspects `document.status === "completed"` (green) vs. other (yellow). It completely ignores `document.error_message`. Failed documents show yellow without error details.<br>3. **Role Gating**: **Missing**. Document deletion (`Trash2` button in `DocumentRow.jsx`) and the Upload navigation item in `Sidebar.jsx` are rendered unconditionally for all users. Backend enforces `MANAGER` role, returning 403 when employees attempt deletion or upload. |
| **Chat Streaming (`/chat/stream`)** | **Partial** | `services/chat.js:streamChat`<br>`pages/Chat/Chat.jsx` | 1. Implemented with `fetch()` + `ReadableStream` reader using `Authorization: Bearer ${token}` header.<br>2. `metadata` and `done` events are handled correctly.<br>3. **Token White-space Stripping Bug**: Line 80 does `data += line.replace("data:", "").trim()`. Trimming removes trailing and leading spaces from tokens, resulting in words running together without spaces (e.g. `"Thequickbrownfox"`). Multi-line token data is also not joined with `\n`.<br>4. **`error` Event Missing**: The switch statement in `chat.js` handles `"metadata"`, `"token"`, `"done"`, but has **no `case "error":`**. When backend yields terminal `event: error`, it falls through to `default: console.log("Unknown SSE Event:", type)`, leaving the UI in an unhandled loading state. |
| **Citation Markers (`[n]`) as Clickable Chips** | **Missing** | `components/chat/MessageBubble.jsx`<br>`components/chat/CitationList.jsx` | `MessageBubble.jsx` simply passes LLM output to `<ReactMarkdown>` without transforming `[n]` bracket markers into interactive chips. In `CitationList.jsx`, citations are rendered as static text badges truncated with `.slice(0, 2)` (only up to 2 citations ever shown). Citation items do not show `page_number`, do not show `snippet`, and are not clickable. |
| **Not-Found Sentence Suppression of Sources** | **Missing** | `components/chat/MessageBubble.jsx`<br>`components/chat/CitationList.jsx` | Although the backend validator strips sources on `I could not find this in the provided documents.`, the frontend has no logic detecting this sentence to ensure source containers and citation cards remain hidden. |
| **Conversation Lifecycle (List, Create, View, Delete)** | **Implemented** | `pages/Chat/Chat.jsx`<br>`components/chat/ChatSidebar.jsx`<br>`services/chat.js` | Complete implementation: loads sessions via `GET /chat/sessions`, opens conversations via `GET /chat/sessions/{id}`, creates new sessions via `sessionId: null`, and deletes conversations via `DELETE /chat/sessions/{id}` with confirmation prompt. |
| **Admin Dashboard (Users, Change Role, Delete, Docs)** | **Partial** | `pages/Users/Users.jsx`<br>`components/users/UserTable.jsx`<br>`components/users/UserRow.jsx`<br>`pages/Dashboard/Dashboard.jsx` | User listing, user creation modal, and user deletion are implemented. Document metrics are visible on the dashboard. However, **Change Role is Missing**: `UserRow.jsx` renders role as a static pill badge. There is no dropdown or action to promote/demote user roles, and `updateUser` is never invoked on this page. |
| **Handling of 401, 403, 409, 503** | **Missing** | `services/api.js`<br>`context/AuthContext.jsx` | No global Axios response interceptor exists. 401 causes silent session failure without redirecting to `/login`. 403 permissions failures display generic toasts. 409 conflict (duplicate document hash) shows unformatted alert/toast. 503 (AI provider exhaustion / DB unavailable) has no dedicated user guidance. |
| **Loading and Empty States** | **Partial** | `components/chat/EmptyChat.jsx`<br>`components/document/EmptyState.jsx`<br>`components/users/EmptyUsers.jsx`<br>`pages/Documents/Documents.jsx` | Chat, user list, and dashboard have good empty and loading states. However, `Documents.jsx` lacks a loading spinner or skeleton while `getDocuments()` is in flight, showing an abrupt empty state before data loads. |

---

## 4. Deprecated Endpoints & Schema Mismatches

### 4.1 Calls to Deprecated Endpoints
1. **`GET /users/me`**
   - **Locations**:
     - `frontend/src/services/auth.js` (line 20): `api.get("/users/me")`
     - `frontend/src/services/user.js` (line 9): `api.get("/users/me")`
   - **Backend Status**: Flagged in `backend/router/user.py` (lines 173–177) as:
     ```python
     @router.get("/me", response_model=UserResponse, deprecated=True, include_in_schema=False)
     ```
   - **Remediation**: Replace both calls with the canonical endpoint `GET /auth/me` defined in `backend/router/auth.py`.

### 4.2 Schema Mismatches

#### 1. `CitationResponse` (`backend/schemas/chat.py`)
- **Backend Schema**:
  ```python
  class CitationResponse(BaseModel):
      document: str
      chunk_index: int
      id: int | None = None
      document_id: int | None = None
      page_number: int | None = None
      snippet: str | None = None
  ```
- **Frontend Mismatch**: In `frontend/src/components/chat/CitationList.jsx`:
  - Only `citation.document` and `citation.chunk_index` are used.
  - `page_number`, `snippet`, `id`, and `document_id` are completely ignored.
  - Array is arbitrarily sliced to 2 items (`citations.slice(0, 2)`), discarding all remaining citations provided by the backend.

#### 2. `Token` Response (`backend/schemas/auth.py`)
- **Backend Schema**:
  ```python
  class Token(BaseModel):
      access_token: str
      token_type: str = "bearer"
      refresh_token: Optional[str] = None
  ```
- **Frontend Mismatch**: Both `frontend/src/pages/Login/Login.jsx` (line 26) and `frontend/src/pages/Signup/Signup.jsx` (line 26) only extract:
  ```javascript
  saveToken(res.data.access_token);
  ```
  `res.data.refresh_token` is dropped on the floor, making refresh token rotation impossible.

#### 3. `UserResponse` (`backend/schemas/user.py`) & AuthContext State Breakage
- **Backend Schema**:
  ```python
  class UserResponse(BaseModel):
      id: int
      name: str
      email: EmailStr
      role: UserRole
      organization: OrganizationInfo
  ```
- **Frontend Mismatches**:
  - **Broken Context State (`AuthContext.jsx`)**:
    In `frontend/src/services/auth.js`:
    ```javascript
    export const me = async () => {
      const res = await api.get("/users/me");
      return res.data; // res.data is the UserResponse object
    };
    ```
    In `frontend/src/context/AuthContext.jsx` lines 19–21:
    ```javascript
    const res = await me();
    setUser(res.data); // BUG: res is already res.data! res.data is undefined!
    ```
    `setUser` sets the authenticated user state to `undefined`. As a result, `useAuth().user` is permanently `undefined` across the application.
  - **Navbar User Display (`Navbar.jsx`)**:
    Line 52 accesses `{currentUser?.username || "User"}`. `UserResponse` has no `username` field (it has `name`). Navbar therefore always displays fallback `"User"`.

#### 4. `DocumentResponse` (`backend/schemas/document.py`)
- **Backend Schema**: Includes `error_message: Optional[str] = None` and `status: str` (`processing`, `completed`, `failed`).
- **Frontend Mismatch**: `DocumentRow.jsx` never reads or renders `document.error_message`.

---

## 5. Security & Network Evaluation

### 5.1 Token Storage
- **Current Mechanism**: `access_token` is stored in browser `window.localStorage` (`frontend/src/utils/token.js`).
- **Security Assessment**: Storing auth tokens in `localStorage` leaves tokens vulnerable to token theft via Cross-Site Scripting (XSS).
- **Recommendation**: For enterprise hardening, migrate to `httpOnly`, `Secure`, `SameSite=Strict` cookies handled automatically by the browser, or store access tokens in application memory with `refresh_token` in an `httpOnly` cookie.

### 5.2 Secrets in Repository
- **Audit Findings**:
  - `backend/.env` is ignored by `.gitignore` and has never been committed.
  - `frontend/.env` is ignored by `.gitignore` and has never been committed.
  - No database passwords, JWT secrets, or provider API keys (`VOYAGE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`) are committed in tracked files.
  - Docker files and configuration safely use environment variable expansion (`${POSTGRES_PASSWORD:-postgres}`).

### 5.3 Backend CORS Configuration vs. Deployed Frontend
- **Backend CORS Configuration** (`backend/app.py` lines 47–50):
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=[
          "http://localhost:5173",
          "https://enterprise-rag-platform-three.vercel.app",
      ],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Assessment**:
  - The deployed production Vercel frontend (`https://enterprise-rag-platform-three.vercel.app`) is **explicitly whitelisted** in `allow_origins`.
  - Local development origin (`http://localhost:5173`) is also present.
  - **Limitation**: Vercel dynamic preview deployments (e.g. `https://enterprise-rag-platform-git-*.vercel.app`) are not whitelisted and will be blocked by CORS unless an `allow_origin_regex` pattern is added.

---

## 6. Prioritised Work List

### P0: Broken & Critical Security / Protocol Fixes

| Task ID | Item | Files to Change | Size | Description |
| :---: | :--- | :--- | :---: | :--- |
| **P0-1** | **Fix `AuthContext` user state & Navbar user display** | `frontend/src/context/AuthContext.jsx`<br>`frontend/src/components/layout/Navbar.jsx` | **S** | In `AuthContext.jsx`, change `setUser(res.data)` to `setUser(res)` so the user state is populated. In `Navbar.jsx`, change `currentUser?.username` to `currentUser?.name`. |
| **P0-2** | **Migrate deprecated `/users/me` to `/auth/me`** | `frontend/src/services/auth.js`<br>`frontend/src/services/user.js` | **S** | Replace calls to deprecated `GET /users/me` with canonical `GET /auth/me`. |
| **P0-3** | **Fix SSE Streaming Parser & Add `error` Event Handler** | `frontend/src/services/chat.js` | **M** | 1. Stop stripping token whitespace with `.trim()`.<br>2. Format incoming token pieces according to the SSE spec (joining multiple `data:` lines with `\n`).<br>3. Add `case "error":` to parse error payloads and dispatch `onError(parsed)`. |
| **P0-4** | **Store Refresh Token & Implement Silent Refresh** | `frontend/src/utils/token.js`<br>`frontend/src/services/api.js`<br>`frontend/src/services/auth.js`<br>`frontend/src/pages/Login/Login.jsx`<br>`frontend/src/pages/Signup/Signup.jsx` | **M** | 1. Add `saveRefreshToken`, `getRefreshToken`, `removeRefreshToken` in `token.js`.<br>2. Save `refresh_token` in `Login.jsx` and `Signup.jsx`.<br>3. Add Axios response interceptor in `api.js` on HTTP 401 to call `POST /auth/refresh`, renew access token, and retry the request; log out if refresh fails. |

---

### P1: Missing Core Capabilities & RBAC Alignment

| Task ID | Item | Files to Change | Size | Description |
| :---: | :--- | :--- | :---: | :--- |
| **P1-1** | **Render `[n]` Citation Markers as Clickable Chips with Modal** | `frontend/src/components/chat/MessageBubble.jsx`<br>`frontend/src/components/chat/CitationList.jsx` | **M** | 1. Parse `[n]` patterns in LLM messages and render interactive clickable chip components.<br>2. Clicking a chip opens a drawer or popover displaying document title, page number, and chunk snippet text.<br>3. In `CitationList.jsx`, remove `.slice(0, 2)` restriction, render all citations, and show page numbers and snippets. |
| **P1-2** | **Document Dashboard Role Gating & Error Messages** | `frontend/src/components/document/DocumentRow.jsx`<br>`frontend/src/components/document/DocumentTable.jsx`<br>`frontend/src/pages/Documents/Documents.jsx`<br>`frontend/src/components/layout/Sidebar.jsx` | **M** | 1. Restrict Delete button in `DocumentRow.jsx` to `MANAGER` role or higher.<br>2. In `Sidebar.jsx`, only show Upload link to `MANAGER` or higher.<br>3. Display `document.error_message` with red badge when status is `failed`. |
| **P1-3** | **Admin Dashboard Role Management** | `frontend/src/components/users/UserRow.jsx`<br>`frontend/src/pages/Users/Users.jsx` | **M** | Add a role selection dropdown in `UserRow.jsx` allowing Admins to change a team member's role via `PUT /users/{user_id}` (`updateUser`). |
| **P1-4** | **Upload Progress Tracking** | `frontend/src/services/document.js`<br>`frontend/src/components/upload/Upload.jsx` | **M** | Pass `onUploadProgress` callback in Axios `uploadDocument` and render a real-time progress bar (0–100%) in `Upload.jsx`. |
| **P1-5** | **Suppress Sources on Not-Found Sentence** | `frontend/src/components/chat/MessageBubble.jsx` | **S** | In `MessageBubble.jsx`, check if message text starts with `"I could not find this in the provided documents."` and suppress `<CitationList>` rendering. |
| **P1-6** | **Redirect to Dashboard after Signup** | `frontend/src/pages/Signup/Signup.jsx` | **S** | Update `Signup.jsx` line 32 to navigate to `/dashboard` immediately after workspace registration instead of redirecting to login. |

---

### P2: Polish, UX & Robustness

| Task ID | Item | Files to Change | Size | Description |
| :---: | :--- | :--- | :---: | :--- |
| **P2-1** | **Centralized HTTP Error Handling (403, 409, 503)** | `frontend/src/services/api.js` | **M** | Add global response interceptor with user-friendly toast messages: 403 (Permission Denied), 409 (Duplicate file detected), 503 (AI/Database service unavailable). |
| **P2-2** | **Document Table Loading Skeleton** | `frontend/src/pages/Documents/Documents.jsx` | **S** | Add skeleton loading state while `getDocuments()` is pending to avoid table flashing. |
| **P2-3** | **Remove Dead Code** | `frontend/src/components/document/UploadBox.jsx` | **S** | Remove orphaned `UploadBox.jsx` component which is not referenced anywhere in the project. |
| **P2-4** | **Base URL Fallback** | `frontend/src/services/api.js`<br>`frontend/src/services/chat.js` | **S** | Provide fallback default `import.meta.env.VITE_API_URL || ""` to avoid `undefined` route requests if env variable is missing. |
| **P2-5** | **Vercel Preview Origin Regex in Backend CORS** | `backend/app.py` | **S** | Add `allow_origin_regex=r"https://enterprise-rag-platform.*\.vercel\.app"` to `CORSMiddleware` in `backend/app.py` to support preview branches. |
