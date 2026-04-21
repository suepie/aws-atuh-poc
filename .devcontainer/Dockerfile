FROM mcr.microsoft.com/devcontainers/typescript-node:22

# Netskope ルートCA証明書をシステム証明書ストアに登録
COPY rootcaCert.pem /usr/local/share/ca-certificates/netskope.crt
RUN update-ca-certificates

# Node.js にも証明書を認識させる
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/netskope.crt

# Lambda用のPython依存パッケージ
RUN if command -v pip3 > /dev/null 2>&1; then \
      pip3 install --no-cache-dir PyJWT[crypto]; \
    fi
