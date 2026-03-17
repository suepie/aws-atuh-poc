#!/bin/bash
# Lambda Authorizer のデプロイパッケージをビルド
# --platform manylinux2014_x86_64 で Lambda (Amazon Linux) 向けバイナリを取得
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
ZIP_FILE="$SCRIPT_DIR/package.zip"

rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

# Lambda (Amazon Linux 2023, x86_64) 向けにインストール
pip install \
  -r "$SCRIPT_DIR/requirements.txt" \
  -t "$BUILD_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  --quiet

# ソースコードをコピー
cp "$SCRIPT_DIR/index.py" "$BUILD_DIR/"

# ZIPパッケージ作成
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -q

echo "Built: $ZIP_FILE"
