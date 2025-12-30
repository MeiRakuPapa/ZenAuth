# 設定（環境変数）

ZenAuth は環境変数で設定します。

- Core ライブラリは `ZENAUTH_` プレフィクス
- サーバ実行時の設定は `ZENAUTH_SERVER_` プレフィクス

## 最低限必要（サーバ）

- `ZENAUTH_SECRET_KEY`（必須）: JWT の署名/検証に使う秘密鍵
- `ZENAUTH_AUTH_SERVER_ORIGIN`（必須）: ZenAuth サーバの公開origin（例: `https://auth.example.com`）
- `ZENAUTH_SERVER_DSN`（必須）: ZenAuth サーバのDB接続（SQLAlchemy DSN）
  - 例（SQLite）: `sqlite+pysqlite:///./zenauth.db`

## よく使う Core 側の設定（`ZENAUTH_`）

- `ZENAUTH_COOKIE_NAME`（既定: `access_token`）
- `ZENAUTH_EXPIRE_MIN`（既定: `15`）
- `ZENAUTH_ALGORITHM`（既定: `HS256`）
- `ZENAUTH_SAMESITE`（既定: `lax`）: `lax` / `none` / `strict`
- `ZENAUTH_SECURE`（既定: `false`）: Cookie の `Secure` フラグ
- `ZENAUTH_AUTH_SERVER_ORIGIN`（必須）: リモート検証URL生成時に使用する origin

## よく使う Server 側の設定（`ZENAUTH_SERVER_`）

- `ZENAUTH_SERVER_REFRESH_WINDOW_SEC`（既定: `300`）

### CORS（サーバ）

- `ZENAUTH_SERVER_CORS_ALLOW_ORIGINS`（既定: 空）: 許可する origin（カンマ区切り）。`*` で全許可。空文字で CORS ミドルウェア無効。
- `ZENAUTH_SERVER_CORS_ALLOW_CREDENTIALS`（既定: `false`）: ブラウザからCookie等を送らせたい場合は `true`
- `ZENAUTH_SERVER_CORS_ALLOW_METHODS`（既定: `*`）: 許可メソッド（カンマ区切り）または `*`
- `ZENAUTH_SERVER_CORS_ALLOW_HEADERS`（既定: `*`）: 許可ヘッダ（カンマ区切り）または `*`

注意: credentials を有効にする場合、origin を `*` にせず明示的に列挙してください。

### CSRF（サーバ）

ブラウザからCookie認証で利用する場合、CSRF対策を推奨します。

- `ZENAUTH_SERVER_CSRF_PROTECT`（既定: `true`）: unsafeメソッド（POST/PUT/PATCH/DELETE）で、認証Cookieが付いている場合に Origin/Referer を検証
- `ZENAUTH_SERVER_CSRF_TRUSTED_ORIGINS`（既定: 空）: 信頼するorigin（カンマ区切り）。空の場合はCORSの許可origin（`*`以外）または同一origin
- `ZENAUTH_SERVER_CSRF_ALLOW_NO_ORIGIN`（既定: `false`）: Origin/Refererが無いリクエストも許可（非推奨）

## ログ関連の設定

- `ZENAUTH_AUDIT_INCLUDE_TOKEN_TIMESTAMPS`（既定: `false`）: `true` の場合、監査ログにリクエストトークン由来の `token_iat` / `token_exp` が含まれることがあります。

### 任意: 初期管理者ユーザーのブートストラップ（opt-in）

開発/デモ用途向けです。

- `ZENAUTH_SERVER_BOOTSTRAP_ADMIN`（既定: `false`）
- `ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER`（既定: `admin`）
- `ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD`（ブートストラップ有効時は必須）

推奨:
- 初回ログイン後すぐにパスワード変更
- 本番環境では有効化しない

## `.env`（任意）

`.env` ファイルの読み込みにも対応していますが、コンテナ環境では Secret 注入などで環境変数を渡す運用が一般的です。
