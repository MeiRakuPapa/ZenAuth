# 使い方

## ZenAuth サーバ起動

1) 必要な環境変数を設定します。

- `ZENAUTH_SECRET_KEY`
- `ZENAUTH_SERVER_DSN`

2) Uvicorn を起動します。

```bash
uvicorn zen_auth.server.run:app --host 0.0.0.0 --port 8000
```

## WebApp 側（サーバーサイド）で Depends として使う

別の FastAPI アプリ（あなたの WebApp）から、ZenAuth サーバーに問い合わせてトークン検証する例です。

```python
from fastapi import Depends, FastAPI

from zen_auth.claims import Claims
from zen_auth.dto import UserDTO

app = FastAPI()

AUTH_VERIFY_TOKEN_URL = "http://auth-server:8000/zen_auth/api/verify/token"


@app.get("/protected")
def protected(user: UserDTO = Depends(Claims.guard(url=AUTH_VERIFY_TOKEN_URL))):
    return {"ok": True, "user_name": user.user_name}
```

補足:
- トークンは Cookie または `Authorization: Bearer <token>` から取得します。

## Claims: FastAPIの依存（認証・認可）

`Claims` は FastAPI の依存として使えるヘルパを提供します。

### 認証（ログイン済みユーザーならOK）

`Claims.guard()` を使うと、トークンを検証して認証済み `UserDTO` を受け取れます。

この依存は、レスポンス側の認証 Cookie を更新（refresh）する挙動も持ちます。

```python
from fastapi import Depends, FastAPI

from zen_auth.claims import Claims
from zen_auth.dto import UserDTO

app = FastAPI()


@app.get("/protected")
def protected(user: UserDTO = Depends(Claims.guard())):
    return {"ok": True, "user_name": user.user_name}
```

### ログイン / ログアウト（Cookie操作）

`Claims.verify_user(...)` は、ZenAuth サーバの `/verify/user` でユーザー認証を行い、成功したら認証 Cookie をセットします。

```python
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

from zen_auth.claims import Claims

app = FastAPI()


class LoginBody(BaseModel):
    user_name: str
    password: str


@app.post("/login")
def login(req: Request, resp: Response, body: LoginBody) -> Response:
    return Claims.verify_user(req, resp, body.user_name, body.password)


@app.post("/logout")
def logout(resp: Response) -> dict:
    Claims.logout(resp)
    return {"ok": True}
```

### ZenAuth のログインUIへリダイレクトする

WebApp 側で ZenAuth ホストのログインページを使う場合は、`app_id` を付けて
`/zen_auth/v1/auth/login_page` へリダイレクトします。

セキュリティ（open redirect 対策）のため、ログインページはユーザー入力の「戻り先URL」を受け取りません。
代わりに、認証サーバ側が `app_id` から戻り先を解決します。

```python
from fastapi import Request
from fastapi.responses import RedirectResponse

from zen_auth.claims import Claims


@app.get("/auth/login")
def start_login(req: Request) -> RedirectResponse:
    url = Claims.login_page_url(req, app_id="my_app")
    return RedirectResponse(url)
```

### ロール必須（RBAC）

`Claims.role(...)` でロールを要求できます。

複数のロール名を指定でき、**いずれか1つでも**満たせばOK（OR）です。

例: `admin` または `viewer` を許可

```python
@app.get("/admin")
def admin_or_viewer(user: UserDTO = Depends(Claims.role("admin", "viewer"))):
    return {"ok": True}

補足:
- ZenAuthServer は、許可なら `200 OK`、必要な role を満たさない場合は `403 Forbidden` を返します。
- `Claims` は `403` を「通常の認可エラー（deny）」として扱います（認可サーバ障害としては扱いません）。それ以外の non-`200` は upstream エラー（`ClaimSourceError`）として扱います。
```

### スコープ必須

`Claims.scope(...)` でスコープを要求できます。

複数のスコープ名を指定でき、**いずれか1つでも**許可されていればOK（OR）です。

```python
@app.get("/reports")
def reports(user: UserDTO = Depends(Claims.scope("read:reports"))):
    return {"ok": True}

補足:
- ZenAuthServer は、許可なら `200 OK`、必要な scope を満たさない場合は `403 Forbidden` を返します。
- `Claims` は `403` を「通常の認可エラー（deny）」として扱います（認可サーバ障害としては扱いません）。それ以外の non-`200` は upstream エラー（`ClaimSourceError`）として扱います。
```

### ロール OR スコープ

`Claims.role_or_scope(...)` を使うと、1つの Depends で「ロールまたはスコープ」の条件を表現できます。

```python
@app.get("/support")
def support(
    user: UserDTO = Depends(Claims.role_or_scope(roles=("admin", "support"), scopes=("support:read",))),
):
    return {"ok": True}

補足:
- 認可サーバの discovery (`/zen_auth/v1/meta/endpoints`) に `verify_user_role_or_scope` があれば、`Claims.role_or_scope(...)` はそれ（role/scope をまとめた verify）を優先して呼びます。
- 無ければ、role verify と scope verify を個別に呼ぶフォールバックで動作します。
- combined endpoint も同様に、`200 OK`=許可、`403 Forbidden`=deny です。
```

### 認可サーバ（ZenAuthサーバ）への向き先

別サービスから ZenAuth サーバへ問い合わせる場合は、以下を設定してください。

- `ZENAUTH_AUTH_SERVER_ORIGIN`（例: `https://auth.example.com`）

`Claims` は、この origin を使って認可サーバのURLを生成します。

### 例外について（最小限）

`Claims.guard()` / `Claims.role()` / `Claims.scope()` は、検証に失敗した場合や認可サーバとの通信に失敗した場合に、`zen_auth.errors` 配下の例外（`ClaimError` とその派生）を送出します。

これをどうHTTPステータスや画面/UIに反映するかは WebApp 側の責務なので、必要に応じて FastAPI の `exception_handler` 等で扱ってください。
