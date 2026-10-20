# JWT-based-authentication-system

Build three endpoints: **register**, **login**, and **me**. Based on the flow described in the GeeksforGeeks article, with a modern Argon2id password hash, PyJWT, and an environment-based signing secret.

Python 3.10+ is required. SQLite is suitable for local learning, not the default choice for a distributed production authentication service.

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Replace `REPLACE_ME` in `.env` with the newly generated secret. **Keep `.env` private and out of version control.**

## Setup (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Replace `REPLACE_ME` in `.env` with the printed secret.

## Run and explore

```bash
uvicorn main:app --reload
```

Open [the API documentation](http://127.0.0.1:8000/docs)

### 1. POST /register

Select **Try it out** and send this JSON body:

```json
{"username":"alex","password":"CorrectHorseBattery99!","full_name":"Alex"}
```

Expect `201` and `{ "username": "alex", "full_name": "Alex" }`.

### 2. POST /login

The login endpoint takes **form data**, not JSON, because it uses `OAuth2PasswordRequestForm`.

- username: `alex`
- password: `CorrectHorseBattery99!`

Expect `200` and a Bearer access token. Do not share this token publicly.

### 3. GET /me

Select the top-right **Authorize** button in Swagger UI, enter the same username/password, and close the popup. Then execute **GET /me**. Expect your profile. Note: Swagger UI's Authorize step calls `/login` itself.

### 4. Test the failure paths

- Duplicate username: `409`
- Invalid password: `401`
- No token to `/me`: `401`
- Invalid or expired JWT: `401`
- Too-short registration password: `422`

### 5. Run automated tests

```bash
pytest -q
```

The tests use a separate temporary SQLite file per test.

## Understand the code in this order

1. `database.py` → `init_db()` creates the table.
2. `database.py` → `create_user()` stores a user, and `get_user()` fetches a dictionary.
3. `main.py` → `RegisterRequest`, `UserPublic`, and `TokenResponse` are input/output contracts.
4. `main.py` → `hash_password()` and `verify_password()` transform/check a password.
5. `main.py` → `create_access_token()` turns a username into a signed and expiring token.
6. `main.py` → `register()` connects validation → hashing → database write.
7. `main.py` → `login()` connects form data → database lookup → password check → token.
8. `main.py` → `get_current_user()` validates token → looks up user.
9. `main.py` → `read_me()` is a protected route using dependency injection.

## Your coding drills (do not use AI autocomplete for the first attempt)

**Drill A:** Write `get_user()` from memory. Can you explain the `?` SQL placeholder and why `(username,)` is a tuple?

**Drill B:** Add `email: str | None` to registration and database table (for a new local DB). Return it in `UserPublic`.

**Drill C:** Change `TOKEN_MINUTES` from 30 to 5. Explain what changes and what does not.

**Drill D:** Add `GET /health`, returning `{ "status": "ok" }`. No authentication required.

**Drill E:** Add a unit test checking that `GET /me` with a random string is rejected with `401`.

## What changes for production?

This project is an instructional starter, **not production-ready authentication**. Real deployments need HTTPS, secrets management, login abuse controls/rate limits, monitoring, database migrations, PostgreSQL/managed storage for horizontal scaling, password reset, email verification, account lifecycle/deactivation, token revocation/rotation (or short-lived tokens plus refresh-token rotation), secure client token storage, authorization rules per resource, and a thorough security review. For public-facing products, prefer an established identity provider/OIDC service rather than implementing your own authentication stack.
