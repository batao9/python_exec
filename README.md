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

### セッション管理（カレントセッション・呼び出し側からの session_id 非公開）

- init ツールを呼ぶと session_id が払い出され、同時に「カレントセッション」に設定されます。
- 呼び出し側は session_id を指定する必要はありません（指定もできません）。各ツールは常にカレントセッションを利用し、存在しない場合は新規作成され、以後も継続利用されます。
- カレントセッションは最後の利用から既定で10分が経過すると（PY_EXEC_SESSION_TTL で変更可）、自動的に新しいセッションに切り替わります（セッションの永続化が有効な環境でも、古いセッションに誤接続しないようにするため）。
- カレントセッションはコンテナ内のマーカー（`/workspace/sessions/.current`）にも保存されるため、プロセスが再起動しても同じ環境を継続できます。
- セッションは最後の利用から既定で10分後に自動削除されます（環境変数 PY_EXEC_SESSION_TTL で変更可能）。
- 同時セッション数の上限は既定で32です（PY_EXEC_SESSION_MAX で変更可能）。
- 明示的なワンショット実行が必要な場合は `run_code_ephemeral` を利用できます（実行後に即時クリーンアップ）。
- セッション操作ツール（最小限）: close_current_session() でカレントセッションを明示的に閉じられます。

主なツール引数:
- run_code(code)
- run_code_ephemeral(code)
- run_file(path)                       # 相対パスはセッション作業領域相対
- cp_in(local_path, container_path=None)  # container_path が相対ならセッション配下
- cp_out(container_path, local_path=None) # container_path が相対ならセッション配下
- edit_file(container_path, content)      # 相対ならセッション配下

reset はコンテナを再作成し、すべてのセッションをクリアします。

