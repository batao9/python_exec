# MCP対応 Python コードインタープリターツール

Model Context Protocol (MCP) に対応した、Docker ベースの Python コード実行およびファイル管理を行う MCP サーバです。

## 特徴
- Docker コンテナ内で Python コードまたはスクリプトを実行  
- コンテナのファイルをホスト作業ディレクトリ（WORKDIR）にダウンロード (`cp_out` ツール)  
- ホスト作業ディレクトリ（WORKDIR）内のファイルをコンテナにアップロード (`cp_in` ツール)  
- コンテナのリセット (`reset` ツール)  
- コンテナにインストールされている Python パッケージを確認 (`list_packages` ツール)  
- コンテナ内のファイルを作成・編集 (`edit_file` ツール)  
- 初期状態のコンテナに MCP Python SDK (`mcp[cli]`) をプリインストール

## 必要要件
- Docker  
- Python 3.10+  
- Conda (optional) または `pip install -r requirements.txt`


### uv を用いたプロジェクトセットアップ

本リポジトリでは、[uv](https://docs.astral.sh/uv/) を用いた Python プロジェクト管理をサポートします。
uv がインストールされていない場合は、次のようにインストールします。
```bash
pip install uv
```
もしくは
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
依存パッケージを追加します。
```bash
uv sync
source .venv/bin/activate
```
## 使い方

以下の手順でサーバを実行およびツールを利用できます。


### 開発モードでの起動

MCP Inspectorを使ってサーバをテスト・デバッグするには:

```bash
mcp dev server.py
```

### サーバの直接起動

```bash
uv run python server.py
```

### コマンドライン引数での作業ディレクトリ指定
`WORKDIR_IN` と `WORKDIR_OUT` をコマンドライン引数で直接指定できます。環境変数や `.env` の設定よりも優先されます。
```bash
python server.py --WORKDIR_IN /path/to/upload/dir --WORKDIR_OUT /path/to/download/dir
```
MCP CLI 経由でも同様に指定可能です:
```bash
mcp dev server.py --WORKDIR_IN /path/to/upload --WORKDIR_OUT /path/to/download
```

### 作業ディレクトリの設定

ファイルのアップロード（cp_in）には `WORKDIR_IN`、ダウンロード（cp_out）には `WORKDIR_OUT` 環境変数で指定されたディレクトリがそれぞれ作業ディレクトリとして扱われます。
どちらも未設定の場合は `WORKDIR` 環境変数、さらに未設定時は現在の作業ディレクトリが使われます。
相対パスのみ許可され、`..` を使って上位ディレクトリへアクセスすることはできません。

例:
```bash
export WORKDIR=/path/to/your/workdir
```
もしくは
```.env
WORKDIR_IN='/path/to/upload/dir'
WORKDIR_OUT='/path/to/downloads/dir'
```

### Docker イメージの指定

コンテナで利用する Python Docker イメージは、`DOCKER_IMAGE` 環境変数または `.env` ファイルで指定できます。
```bash
export DOCKER_IMAGE=python:3.13-slim
```
もしくは
```.env
DOCKER_IMAGE='python:3.13-slim'
```

### MCP Inspectorによるテスト
```bash
mcp dev server.py
```


## 推奨 Docker イメージ (データ分析向け)
```bash
docker build -t code_interpreter .
```

ほかのイメージを利用したい場合、以下のような Docker イメージがおすすめです。  
- jupyter/scipy-notebook: Jupyter Notebook や数値計算向けパッケージがプリインストールされた公式イメージ  
- continuumio/miniconda3: Conda 環境で柔軟にパッケージを管理できるイメージ  
- python:3.13-slim ベースに `pip install numpy pandas scipy scikit-learn matplotlib seaborn jupyter plotly` を行うカスタムイメージ

### セッションとエフェメラルワークスペース（新機能）

- init ツールを呼ぶと session_id が払い出されます。以降のツール呼び出しに session_id を渡すと、
  コンテナ内の `/workspace/sessions/<session_id>/` 以下がその応答専用の作業領域になります。
- session_id を省略すると、各ツール呼び出しごとに一時セッションが自動作成され、処理完了後に即削除されます。
- セッションは最後の利用から既定で10分後に自動削除されます（環境変数 PY_EXEC_SESSION_TTL で変更可能）。
- 同時セッション数の上限は既定で32です（PY_EXEC_SESSION_MAX で変更可能）。

主なツール引数の違い:
- run_code(code, session_id=None)
- run_file(path, session_id=None)  # 相対パスはセッション作業領域相対
- cp_in(local_path, container_path=None, session_id=None)  # container_path が相対ならセッション配下
- cp_out(container_path, local_path=None, session_id=None) # container_path が相対ならセッション配下
- edit_file(container_path, content, session_id=None)      # 相対ならセッション配下

不要になったセッションは close_session(session_id) で即時削除できます。reset はコンテナを再作成し、すべてのセッションをクリアします。

