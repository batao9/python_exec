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
依存パッケージを追加します。
```bash
uv sync

## 使い方

以下の手順でサーバを実行およびツールを利用できます。

### 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 開発モードでの起動

MCP Inspectorを使ってサーバをテスト・デバッグするには:

```bash
mcp dev server.py
```

### サーバの直接起動

```bash
uv run python server.py
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
