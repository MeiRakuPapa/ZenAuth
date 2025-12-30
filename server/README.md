# ZenAuth-server

Server-side components for the ZenAuth monorepo.

日本語: see `README_ja.md`.

For how to run the server (Uvicorn) and environment variables, see the repository root README.

- Repository: https://github.com/MeiRakuPapa/ZenAuth

## Bulk import (CSV)

You can bulk create/update users/apps/roles/scopes from CSV.

Script:

- `server/src/scripts/import_csv.py`

### Usage

```bash
python server/src/scripts/import_csv.py \
	--dsn "sqlite+pysqlite:////absolute/path/to/zenauth.sqlite3" \
	--roles roles.csv \
	--scopes scopes.csv \
	--apps apps.csv \
	--users users.csv
```

- `--mode create` fails if a record already exists.
- `--mode upsert` (default) creates or updates.

### CSV formats

#### roles.csv

Headers:

- `role_name` (required)
- `display_name` (optional, defaults to `role_name`)
- `description` (optional)
- `scopes` (optional, comma-separated scope names; binds scopes to the role)

#### scopes.csv

Headers:

- `scope_name` (required)
- `display_name` (optional, defaults to `scope_name`)
- `description` (optional)
- `roles` (optional, comma-separated role names; binds roles to the scope)

#### apps.csv

Headers:

- `app_id` (required)
- `display_name` (optional)
- `description` (optional)
- `return_to` (required; absolute http(s) URL or absolute path starting with `/`)

#### users.csv

Headers:

- `user_name` (required)
- `password` (required for new users)
- `roles` (optional, comma-separated role names)
- `real_name` (optional)
- `division` (optional)
- `description` (optional)
- `policy_epoch` (optional; used for new users; default=1)

If passwords are already hashed (bcrypt), pass `--password-already-hashed`.
