# ZenAuth Example WebApp (FastAPI)

ZenAuthServer を「認証サーバ」として利用する、最小の WebApp サンプルです。

- `/auth/login` で ZenAuth のログインUI (`/zen_auth/v1/auth/login_page`) にリダイレクト
- ログイン後の遷移先 `/after_login`（または `/protected`）でユーザー名を表示
- role/scope で制限されたページへのリンクを用意（認可エラーの挙動確認用）
- `Claims.guard()` / `Claims.role()` / `Claims.scope()` で保護
- HTML生成は ZenHtml (`zen_html`) を使用

## 事前条件

- ZenAuthServer が起動していること（例: `http://localhost:8000`）
- WebApp 側から ZenAuthServer の discovery (`/zen_auth/v1/meta/endpoints`) にアクセスできること

## 起動

別ターミナルで ZenAuthServer を起動してから、WebApp を起動します。

### WebApp

```bash
export ZENAUTH_AUTH_SERVER_ORIGIN="http://localhost:8000"
uvicorn examples.webapp_fastapi.app:app --reload --port 9000
```

- WebApp: `http://localhost:9000/`
- ZenAuthServer: `http://localhost:8000/`

## `return_to` の設定（重要）

ZenAuthServer は open redirect 対策のため、ログイン後の戻り先を `app_id` から解決します。
このサンプルでユーザー名が見えるページに戻すには、client app の `return_to` を以下に設定してください。

- `http://localhost:9000/after_login`（推奨）

設定後、WebApp のトップから **Login** を押してください。

## ZenAuthServer 側の準備（admin UI）

このサンプルを一通り試すには、ZenAuthServer 側で **app / user / role / scope** を揃えるのが基本になります。

1. ZenAuth の admin UI にログインできる状態にします。
	- Admin UI: `http://localhost:8000/zen_auth/v1/admin/`
	- まだ admin ユーザーが無い場合は、bootstrap admin を有効にして起動します。
	  - 参照: [README_ja.md](../../README_ja.md)（`ZENAUTH_SERVER_BOOTSTRAP_ADMIN*` の環境変数）
2. Apps で client app を作成/更新します。
	- `app_id`: `example_webapp`
	- `return_to`: `http://localhost:9000/after_login`
3. Scopes で scope を作成します。
	- `example:read`
4. Users でユーザーを作成/更新し、必要な権限を付与します。
	- `/protected/admin` を通したい → role `admin` を付与
	- `/protected/scope` を通したい → scope `example:read` を付与

準備できたら `http://localhost:9000/` から **Login** を押して動作確認できます。

## role/scope のデモ

`/after_login`（または `/protected`）から次を試せます。

- `/protected/admin`（role: `admin` が必要）
- `/protected/scope`（scope: `example:read` が必要）
- `/protected/role_or_scope`（role `admin` または scope `example:read` のどちらかでOK）

### 未定義 role/scope での挙動テスト

- `/protected/fake_role`（存在しない role: `fake_role` が必要）
- `/protected/fake_scope`（存在しない scope: `fake_scope` が必要）
- `/protected/fake_role_or_scope`（どちらも未定義な role/scope で保護）

これら未定義の role/scope でアクセスすると、認可エラー（403 Forbidden）となり、HTMLのエラーページが表示されます。例外や500エラーにはなりません。安全な挙動です。

## メモ

- Cookie は「ドメイン」に紐づくので、ローカル開発で `localhost` 同士ならポートが違ってもブラウザが送ってくれます。
- 本番で WebApp と ZenAuthServer が別ドメインの場合は、Cookie 共有はできないので別方式（例: 同一ドメイン配下、あるいはフロント/バックの構成）を検討してください。
