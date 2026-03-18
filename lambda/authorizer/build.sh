#!/bin/bash
# Lambda Authorizer のデプロイパッケージをビルド
# venv + --platform manylinux2014_x86_64 で Lambda (Amazon Linux) 向けバイナリを取得
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
ZIP_FILE="$SCRIPT_DIR/package.zip"
VENV_DIR="$SCRIPT_DIR/.venv"

rm -rf "$BUILD_DIR" "$ZIP_FILE"
mkdir -p "$BUILD_DIR"

# venv作成（なければ）
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# venvのpipでLambda向けにインストール
"$VENV_DIR/bin/pip" install \
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
