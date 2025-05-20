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

## インストール

```bash
conda create -n mcp python=3.13 pip -y
conda activate mcp
pip install -r requirements.txt
```

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
python server.py
# または
mcp run server.py
```

### 作業ディレクトリの設定

ファイルのアップロード・ダウンロードでは、WORKDIR 環境変数で指定されたディレクトリが作業ディレクトリとして扱われます。
相対パスのみ許可され、`..` を使って上位ディレクトリへアクセスすることはできません。

例:
```bash
export WORKDIR=/path/to/your/workdir
python server.py
```

### Docker イメージの指定

コンテナで利用する Python Docker イメージは、`DOCKER_IMAGE` 環境変数または `.env` ファイルで指定できます。
```bash
export DOCKER_IMAGE=python:3.9-slim
python server.py
```

### Claude Desktopへのインストール

```bash
mcp install server.py
```

- カスタム名を指定: `--name`

```bash
mcp install server.py --name "Docker Code Interpreter"
```

- 環境変数を指定: `-v` または `-f .env`

```bash
mcp install server.py -v API_KEY=abc123 -f .env
```

### ツールの実行例

```bash
mcp run server.py run_code -- --code "print('Hello from Docker')"
```

```bash
mcp run server.py list_packages
```
```bash
mcp run server.py edit_file -- --container_path report.txt --content "Updated content"
```

## テスト

```bash
python -m unittest
```

## 推奨 Docker イメージ (データ分析向け)

データ分析や機械学習の用途には、以下の Python パッケージがよく利用されます。
- numpy: 数値計算
- pandas: データフレーム操作
- scipy: 科学計算
- scikit-learn: 機械学習
- matplotlib: 基本的な可視化
- seaborn: 統計可視化
- jupyter：インタラクティブ実行環境
- plotly: 対話型可視化

これらをまとめて利用したい場合、以下のような Docker イメージがおすすめです。  
- jupyter/scipy-notebook: Jupyter Notebook や上記パッケージがプリインストールされた公式イメージ  
- continuumio/miniconda3: Conda 環境で柔軟にパッケージを管理できるイメージ  
- python:3.10-slim ベースに `pip install numpy pandas scipy scikit-learn matplotlib seaborn jupyter plotly` を行うカスタムイメージ
