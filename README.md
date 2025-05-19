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

```bash

```
