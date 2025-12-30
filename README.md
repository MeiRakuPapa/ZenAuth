
![Python](https://img.shields.io/badge/Python-3.10%20|%203.11%20|%203.12-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?logo=black&logoColor=white)](https://github.com/psf/black)
[![flake8](https://img.shields.io/badge/lint-flake8-blueviolet.svg?logo=flake8&logoColor=white)](https://flake8.pycqa.org/)
![Typing](https://img.shields.io/badge/Typing-mypy-blue.svg)
![Tests](https://img.shields.io/badge/Tests-Passed-brightgreen.svg)

# ZenAuth

ZenAuth is a JWT-based authentication and user management system for Python/FastAPI.

ZenAuth is intentionally simplified for self-hosted, internal authentication use cases.
It does not aim to be a full standards-compliant identity provider (e.g. OAuth2/OIDC).

It is not designed to be exposed directly to the public internet without additional hardening and operational controls.

This repository is a monorepo containing:

- **ZenAuth-server**: FastAPI server implementation (login/verify/admin endpoints)
- **ZenAuth**: core library (claims, DTOs, config)

## Features
- **JWT Authentication**: Secure token-based authentication.
- **Role-Based Access Control (RBAC)**: Fine-grained access control for users.
- **Flexible User Management**: Easily manage users, roles, and permissions.
- **Configurable**: Environment-based configuration for different deployment scenarios.
- **Extensible**: Add new providers or extend existing functionality with ease.

## Installation

### From PyPI (recommended)

Pick what you need:

- Run the ZenAuth server:
   ```bash
   pip install zenauth-server
   ```
- Use remote token validation in your WebApp (server-side `Depends`):
   ```bash
   pip install ZenAuth
   ```

### From source (development)

```bash
git clone https://github.com/MeiRakuPapa/ZenAuth.git
cd ZenAuth

python -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e core -e "server[test]"
```

## Usage

### Run the server

Set environment variables (see below), then:

```bash
uvicorn zen_auth.server.run:app --host 0.0.0.0 --port 8000
```

Notes:

- The server can optionally bootstrap an initial admin user on first startup (when the user does not already exist).
- This is intended for development/demo use. Change the password immediately and do not use this behavior in production.

Example:

```bash
export ZENAUTH_SERVER_BOOTSTRAP_ADMIN=true
export ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER=admin
export ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD='change-me-now'
```

### Use ZenAuth in your WebApp (server-side)

In another FastAPI application, you can validate tokens by calling the ZenAuth server.

```python
from fastapi import Depends, FastAPI

from zen_auth.claims import Claims
from zen_auth.dto import UserDTO

app = FastAPI()

AUTH_VERIFY_TOKEN_URL = "http://auth-server:8000/zen_auth/api/verify/token"


@app.get("/protected")
def protected(user: UserDTO = Depends(Claims.guard(url=AUTH_VERIFY_TOKEN_URL))):
   return {"ok": True, "user_name": user.user_name}


@app.get("/admin")
def admin_only(
   user: UserDTO = Depends(
      Claims.role("admin", url=AUTH_VERIFY_TOKEN_URL)
   )
):
   return {"ok": True}
```

Notes:

- `Claims` reads the token from cookie or `Authorization: Bearer <token>`.
- On success, it refreshes the cookie in the response.

### Running Tests
To run the test suite:
```bash
pytest
```

## Configuration
ZenAuth is configured via environment variables.

- Details: `docs/CONFIGURATION.md`
- Usage guide: `docs/USAGE.md`

## Production notes

These are common pitfalls when deploying ZenAuth in production.

- **Secrets**: Set a strong `ZENAUTH_SECRET_KEY` and keep it confidential.
- **Auth server origin**: Set `ZENAUTH_AUTH_SERVER_ORIGIN` to the public origin of the ZenAuth server (used for URL generation).
- **HTTPS cookies**: Set `ZENAUTH_SECURE=true`. If you need cross-origin cookie auth from browsers, you will typically need `ZENAUTH_SAMESITE=none` + HTTPS.
- **Bootstrap admin**: Keep `ZENAUTH_SERVER_BOOTSTRAP_ADMIN=false` in production.
- **CORS**: Do not use permissive CORS in production. Restrict allowed origins to your WebApp.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

Maintainer: Yusuke KITAGAWA (https://github.com/MeiRakuPapa)

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Built with Python, FastAPI, and SQLAlchemy.
- Inspired by modern authentication systems.
