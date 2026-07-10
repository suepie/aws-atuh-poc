#!/bin/bash
# SPI JAR ビルドスクリプト
# 前提：Maven 3.9+ + JDK 17+

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building Last Login Tracker SPI ==="
echo "Working directory: $(pwd)"

# Java バージョン確認
echo ""
echo "Java version:"
java -version 2>&1 | head -1

echo ""
echo "Maven version:"
mvn --version 2>&1 | head -1

echo ""
echo "=== mvn clean package ==="
mvn clean package -DskipTests

if [ -f "target/last-login-tracker.jar" ]; then
    echo ""
    echo "✅ Build successful"
    echo "JAR: $(ls -la target/last-login-tracker.jar)"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Keycloak: cd ../.. && docker compose restart keycloak"
    echo "  2. Verify SPI loaded: docker compose logs keycloak | grep last-login-tracker"
    echo "  3. Run V3' test: cd ../.. && ./tests/v3-custom-authenticator.sh"
else
    echo ""
    echo "❌ Build failed - JAR not found"
    exit 1
fi
