
![Python](https://img.shields.io/badge/Python-3.10%20|%203.11%20|%203.12-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?logo=black&logoColor=white)](https://github.com/psf/black)
[![flake8](https://img.shields.io/badge/lint-flake8-blueviolet.svg?logo=flake8&logoColor=white)](https://flake8.pycqa.org/)
![Typing](https://img.shields.io/badge/Typing-mypy-blue.svg)
![Tests](https://img.shields.io/badge/Tests-Passed-brightgreen.svg)

# ZenAuth

ZenAuth は、Python/FastAPI 向けの JWT 認証・ユーザー管理ライブラリです。

ZenAuth は、組織内で完結する認証運用（self-hosted / internal）に寄せて意図的に簡略化しています。
OAuth2/OIDC などの標準にフル準拠した IdP を目指すものではありません。

また、追加のハードニングや運用上の対策なしに、インターネットへ直接公開することは想定していません。

このリポジトリはモノレポで、以下のパッケージで構成されています。

- **ZenAuth-server**: FastAPI サーバー実装（login/verify/admin など）
- **ZenAuth**: コアライブラリ（claims, DTO, config）

## 特徴
- **簡単な統合**: FastAPIや他のPythonフレームワークと簡単に統合可能。
- **JWTサポート**: JSON Web Tokenを使用した認証。
- **拡張性**: カスタムプロバイダーやストレージバックエンドを簡単に追加可能。
- **セキュリティ**: 安全なパスワードハッシュとトークン管理。

## インストール

### PyPIから（推奨）

用途に応じて必要なものだけインストールします。

- ZenAuth サーバーを起動したい:
    ```bash
    pip install zenauth-server
    ```
- 自分の WebApp（サーバーサイド）でリモート検証を `Depends` で使いたい:
    ```bash
    pip install ZenAuth
    ```

### ソースから（開発用）

```bash
git clone https://github.com/MeiRakuPapa/ZenAuth.git
cd ZenAuth

python -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e core -e "server[test]"
```

## 使い方

### サーバー起動

必要な環境変数（下記参照）を設定してから、以下で起動できます。

```bash
uvicorn zen_auth.server.run:app --host 0.0.0.0 --port 8000
```

補足:

- 初回起動時に（ユーザーが存在しない場合）初期管理者ユーザーをブートストラップ作成できます（任意）。
- これは開発/デモ用途向けです。起動後すぐにパスワードを変更し、本番環境では使用しないでください。

例:

```bash
export ZENAUTH_SERVER_BOOTSTRAP_ADMIN=true
export ZENAUTH_SERVER_BOOTSTRAP_ADMIN_USER=admin
export ZENAUTH_SERVER_BOOTSTRAP_ADMIN_PASSWORD='change-me-now'
```

### WebApp 側（サーバーサイド）で Depends として使う（ZenAuth）

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


@app.get("/admin")
def admin_only(
    user: UserDTO = Depends(
        Claims.role("admin", url=AUTH_VERIFY_TOKEN_URL)
    )
):
    return {"ok": True}
```

補足:

- トークンは Cookie または `Authorization: Bearer <token>` から取得します。
- 成功時は、レスポンスに更新済み Cookie をセットします。

## 設定

ZenAuth は環境変数で設定します。

- 詳細: `docs/CONFIGURATION_ja.md`
- 使い方: `docs/USAGE_ja.md`

## Production notes（本番運用の注意）

本番環境にデプロイする際にハマりやすいポイントです。

- **秘密情報**: 強力な `ZENAUTH_SECRET_KEY` を設定し、漏えいしないように管理する。
- **Auth server origin**: `ZENAUTH_AUTH_SERVER_ORIGIN` に、ZenAuth サーバの公開originを設定（URL生成に利用）。
- **HTTPS Cookie**: `ZENAUTH_SECURE=true` を推奨。ブラウザからクロスオリジンのCookie認証をしたい場合、通常は `ZENAUTH_SAMESITE=none` + HTTPS が必要。
- **bootstrap admin**: 本番では `ZENAUTH_SERVER_BOOTSTRAP_ADMIN=false` を推奨。
- **CORS**: 本番では permissive な CORS を避け、WebApp の origin に限定する。

## コントリビュート
バグ報告や機能リクエストは、[GitHubリポジトリ](https://github.com/MeiRakuPapa/ZenAuth)で受け付けています。プルリクエストも歓迎します！

Maintainer: Yusuke KITAGAWA（https://github.com/MeiRakuPapa）

## ライセンス
このプロジェクトは、MITライセンスの下で提供されています。
