# MCP対応 Python コードインタープリターツール

Model Context Protocol (MCP) に対応した、Docker ベースの Python コード実行およびファイル管理を行う MCP サーバです。

## 特徴
- Docker コンテナ内で Python コードまたはスクリプトを実行  
- 成果物（画像など）をホストにコピー (`cp_out` ツール)  
- ホスト上のファイルをコンテナにアップロード (`cp_in` ツール)  
- コンテナのリセット (`reset` ツール)  
- コンテナに Python パッケージを追加インストール (`install` ツール)  
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

## テスト

```bash
python -m unittest
```
