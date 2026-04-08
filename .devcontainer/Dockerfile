FROM mcr.microsoft.com/devcontainers/typescript-node:22

# Lambda用のPython依存パッケージ
RUN if command -v pip3 > /dev/null 2>&1; then \
      pip3 install --no-cache-dir PyJWT[crypto]; \
    fi
