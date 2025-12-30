# ZenAuth-server

ZenAuth モノレポの server 側コンポーネントです。

サーバの起動方法（Uvicorn）や環境変数については、リポジトリルートの README を参照してください。

- Repository: https://github.com/MeiRakuPapa/ZenAuth

## CSV一括投入（Bulk import）

CSV から user / app / role / scope を一括で作成・更新できます。

スクリプト:

- `server/src/scripts/import_csv.py`

### 使い方

```bash
python server/src/scripts/import_csv.py \
  --dsn "sqlite+pysqlite:////absolute/path/to/zenauth.sqlite3" \
  --roles roles.csv \
  --scopes scopes.csv \
  --apps apps.csv \
  --users users.csv
```

- `--mode create`: 既に存在する場合はエラー
- `--mode upsert`（デフォルト）: 無ければ作成、あれば更新

### CSVフォーマット

#### roles.csv

ヘッダ:

- `role_name`（必須）
- `display_name`（任意。省略時は `role_name`）
- `description`（任意）
- `scopes`（任意。カンマ区切りの scope 名。role に scope を紐付けます）

#### scopes.csv

ヘッダ:

- `scope_name`（必須）
- `display_name`（任意。省略時は `scope_name`）
- `description`（任意）
- `roles`（任意。カンマ区切りの role 名。scope に role を紐付けます）

#### apps.csv

ヘッダ:

- `app_id`（必須）
- `display_name`（任意）
- `description`（任意）
- `return_to`（必須。絶対 http(s) URL または `/` で始まる絶対パス）

#### users.csv

ヘッダ:

- `user_name`（必須）
- `password`（新規作成時は必須）
- `roles`（任意。カンマ区切りの role 名）
- `real_name`（任意）
- `division`（任意）
- `description`（任意）
- `policy_epoch`（任意。新規作成時に使用。デフォルト=1）

password が既に bcrypt ハッシュの場合は `--password-already-hashed` を指定してください。
