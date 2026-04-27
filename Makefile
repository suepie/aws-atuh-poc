.PHONY: help \
	tf-init tf-plan tf-apply tf-destroy tf-output \
	tf-init-dr tf-plan-dr tf-apply-dr tf-destroy-dr \
	tf-init-kc tf-plan-kc tf-apply-kc tf-destroy-kc \
	tf-init-all tf-apply-all tf-destroy-all tf-output-all \
	lambda-build lambda-build-authorizer lambda-build-backend lambda-build-pre-token \
	deploy-backend \
	kc-build kc-push kc-deploy kc-redeploy kc-status kc-logs kc-exec kc-admin-url kc-public-url \
	app-env app-kc-env \
	app-dev app-kc-dev app-sso-dev \
	cognito-create-test-users cognito-list-users \
	keycloak-users-guide \
	logs-authorizer logs-backend logs-pre-token logs-keycloak \
	ip-show ip-add ip-add-provider ip-add-public ip-add-public-provider ip-set-my-ip ip-clear \
	status sso-login \
	clean

# ==============================================================================
# 設定
# ==============================================================================

AWS_REGION         := ap-northeast-1
TF_INFRA_DIR       := infra
TF_DR_DIR          := infra/dr-osaka
TF_KC_DIR          := infra/keycloak

LAMBDA_AUTHORIZER  := lambda/authorizer
LAMBDA_BACKEND     := lambda/backend
LAMBDA_PRE_TOKEN   := lambda/pre-token

APP_COGNITO        := app
APP_KEYCLOAK       := app-keycloak
APP_SSO_PEER       := app-sso-peer

KC_CLUSTER         := auth-poc-kc-cluster
KC_SERVICE         := auth-poc-kc-service
KC_DOCKER_DIR      := keycloak
KC_IMAGE_NAME      := auth-poc-kc

LOG_SINCE          ?= 10m

# ==============================================================================
# [tf-*] Terraform: 東京（Cognito + Lambda + API Gateway）
# ==============================================================================

tf-init: ## [terraform] 東京インフラ初期化
	cd $(TF_INFRA_DIR) && terraform init

tf-plan: lambda-build ## [terraform] 東京インフラ変更確認
	cd $(TF_INFRA_DIR) && terraform plan -out=tfplan

tf-apply: lambda-build ## [terraform] 東京インフラ適用
	cd $(TF_INFRA_DIR) && terraform apply -auto-approve

tf-destroy: ## [terraform] 東京インフラ削除
	cd $(TF_INFRA_DIR) && terraform destroy

tf-output: ## [terraform] 東京インフラ output 表示
	cd $(TF_INFRA_DIR) && terraform output

# ==============================================================================
# [tf-*-dr] Terraform: 大阪DR
# ==============================================================================

tf-init-dr: ## [terraform] 大阪DRインフラ初期化
	cd $(TF_DR_DIR) && terraform init

tf-plan-dr: ## [terraform] 大阪DRインフラ変更確認
	cd $(TF_DR_DIR) && terraform plan -out=tfplan

tf-apply-dr: ## [terraform] 大阪DRインフラ適用
	cd $(TF_DR_DIR) && terraform apply -auto-approve

tf-destroy-dr: ## [terraform] 大阪DRインフラ削除
	cd $(TF_DR_DIR) && terraform destroy

# ==============================================================================
# [tf-*-kc] Terraform: Keycloak（ECS + RDS + ALB）
# ==============================================================================

tf-init-kc: ## [terraform] Keycloakインフラ初期化
	cd $(TF_KC_DIR) && terraform init

tf-plan-kc: ## [terraform] Keycloakインフラ変更確認
	cd $(TF_KC_DIR) && terraform plan -out=tfplan

tf-apply-kc: ## [terraform] Keycloakインフラ適用
	cd $(TF_KC_DIR) && terraform apply -auto-approve

tf-destroy-kc: ## [terraform] Keycloakインフラ削除
	cd $(TF_KC_DIR) && terraform destroy

# ==============================================================================
# [tf-*-all] 3スタック一括
# ==============================================================================

tf-init-all: tf-init tf-init-dr tf-init-kc ## [terraform] 3スタック全初期化

tf-apply-all: tf-apply tf-apply-kc ## [terraform] 3スタック全適用（DR除く）

tf-destroy-all: tf-destroy-kc tf-destroy-dr tf-destroy ## [terraform] 3スタック全削除

tf-output-all: ## [terraform] 全スタックの output 表示
	@echo "=== 東京 infra ==="
	@cd $(TF_INFRA_DIR) && terraform output 2>/dev/null || echo "(not initialized)"
	@echo ""
	@echo "=== 大阪 DR ==="
	@cd $(TF_DR_DIR) && terraform output 2>/dev/null || echo "(not initialized)"
	@echo ""
	@echo "=== Keycloak ==="
	@cd $(TF_KC_DIR) && terraform output 2>/dev/null || echo "(not initialized)"

# ==============================================================================
# [lambda-*] Lambda パッケージビルド
# ==============================================================================

lambda-build: lambda-build-authorizer lambda-build-backend ## [lambda] 全Lambda パッケージをビルド

lambda-build-authorizer: ## [lambda] Authorizer パッケージをビルド (PyJWT含む)
	bash $(LAMBDA_AUTHORIZER)/build.sh

lambda-build-backend: ## [lambda] Backend パッケージをビルド
	cd $(LAMBDA_BACKEND) && rm -f package.zip && zip -j package.zip index.py -q
	@echo "Built: $(LAMBDA_BACKEND)/package.zip"

lambda-build-pre-token: ## [lambda] Pre Token Generation パッケージをビルド（archive_file で自動生成のため通常不要）
	@echo "Pre Token Lambda は terraform archive_file で自動ビルドされます"

# ==============================================================================
# [deploy-*] デプロイショートカット
# ==============================================================================

deploy-backend: lambda-build ## [deploy] Lambda コード再ビルド + 東京インフラ適用
	cd $(TF_INFRA_DIR) && terraform apply -auto-approve

# ==============================================================================
# [kc-*] Keycloak 管理
# ==============================================================================

kc-build: ## [keycloak] Docker イメージビルド
	cd $(KC_DOCKER_DIR) && docker build --platform linux/amd64 -t $(KC_IMAGE_NAME) .

kc-push: kc-build ## [keycloak] ECR にログイン + イメージ push
	$(eval ECR_URL := $(shell cd $(TF_KC_DIR) && terraform output -raw ecr_repository_url))
	$(eval ACCOUNT_ID := $(shell echo $(ECR_URL) | cut -d. -f1))
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	docker tag $(KC_IMAGE_NAME):latest $(ECR_URL):latest
	docker push $(ECR_URL):latest
	@echo "Pushed: $(ECR_URL):latest"

kc-deploy: kc-push kc-redeploy ## [keycloak] ビルド → push → ECS再デプロイ

kc-redeploy: ## [keycloak] ECS サービスを force new deployment
	aws ecs update-service \
		--cluster $(KC_CLUSTER) \
		--service $(KC_SERVICE) \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--no-cli-pager \
		--query 'service.{desired:desiredCount,running:runningCount}' --output json

kc-status: ## [keycloak] ECS/ALB/RDS の状態を表示
	@echo "=== ECS Service ==="
	@aws ecs describe-services --cluster $(KC_CLUSTER) --services $(KC_SERVICE) --region $(AWS_REGION) \
		--query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount,rolloutState:deployments[0].rolloutState}' \
		--output table --no-cli-pager
	@echo ""
	@echo "=== ALB Target Health ==="
	@PUB_TG=$$(aws elbv2 describe-target-groups --names auth-poc-kc-tg --region $(AWS_REGION) --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null); \
	 ADMIN_TG=$$(aws elbv2 describe-target-groups --names auth-poc-kc-admin-tg --region $(AWS_REGION) --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null); \
	 echo "Public ALB:  $$(aws elbv2 describe-target-health --target-group-arn $$PUB_TG --region $(AWS_REGION) --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null)"; \
	 echo "Admin ALB:   $$(aws elbv2 describe-target-health --target-group-arn $$ADMIN_TG --region $(AWS_REGION) --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null)"
	@echo ""
	@echo "=== RDS ==="
	@aws rds describe-db-instances --db-instance-identifier auth-poc-kc-db --region $(AWS_REGION) \
		--query 'DBInstances[0].DBInstanceStatus' --output text --no-cli-pager

kc-logs: ## [keycloak] Keycloak ECS のログ (LOG_SINCE=10m で期間指定)
	aws logs tail /ecs/auth-poc-kc --since $(LOG_SINCE) --follow --region $(AWS_REGION) --no-cli-pager

kc-exec: ## [keycloak] ECS Exec でコンテナに入る
	@TASK_ID=$$(aws ecs list-tasks --cluster $(KC_CLUSTER) --desired-status RUNNING --region $(AWS_REGION) --query 'taskArns[0]' --output text | awk -F'/' '{print $$NF}'); \
	echo "Task: $$TASK_ID"; \
	aws ecs execute-command \
		--cluster $(KC_CLUSTER) \
		--task $$TASK_ID \
		--container keycloak \
		--region $(AWS_REGION) \
		--interactive \
		--command "/bin/bash"

kc-admin-url: ## [keycloak] Admin Console URL を表示（IP制限あり）
	@cd $(TF_KC_DIR) && terraform output -raw keycloak_admin_url 2>/dev/null || echo "Run 'make tf-apply-kc' first"
	@echo ""

kc-public-url: ## [keycloak] 公開 URL を表示
	@cd $(TF_KC_DIR) && terraform output -raw keycloak_public_url 2>/dev/null || echo "Run 'make tf-apply-kc' first"
	@echo ""

# ==============================================================================
# [app-*] SPA 開発サーバーと .env 自動生成
# ==============================================================================

app-env: ## [app] app/.env を terraform output から自動生成（Cognito + Keycloak 統合版）
	@cd $(TF_INFRA_DIR) && \
		AUTHORITY=$$(terraform output -raw cognito_issuer); \
		CLIENT_ID=$$(terraform output -raw cognito_client_id); \
		DOMAIN=$$(terraform output -raw cognito_domain); \
		LOCAL_AUTHORITY=$$(terraform output -raw local_cognito_issuer); \
		LOCAL_CLIENT_ID=$$(terraform output -raw local_cognito_client_id); \
		LOCAL_DOMAIN=$$(terraform output -raw local_cognito_domain); \
		API_ENDPOINT=$$(terraform output -raw api_gateway_url); \
		KC_AUTHORITY=$$(cd ../$(TF_KC_DIR) && terraform output -raw keycloak_oidc_issuer 2>/dev/null || echo ""); \
		printf "VITE_COGNITO_AUTHORITY=%s\nVITE_COGNITO_CLIENT_ID=%s\nVITE_COGNITO_DOMAIN=%s\nVITE_REDIRECT_URI=http://localhost:5173/callback\nVITE_POST_LOGOUT_URI=http://localhost:5173/\n\nVITE_AUTH0_IDP_NAME=Auth0\n\nVITE_LOCAL_COGNITO_AUTHORITY=%s\nVITE_LOCAL_COGNITO_CLIENT_ID=%s\nVITE_LOCAL_COGNITO_DOMAIN=%s\n\nVITE_KEYCLOAK_AUTHORITY=%s\nVITE_KEYCLOAK_CLIENT_ID=auth-poc-spa\n\nVITE_API_ENDPOINT=%s\n" \
			"$$AUTHORITY" "$$CLIENT_ID" "$$DOMAIN" \
			"$$LOCAL_AUTHORITY" "$$LOCAL_CLIENT_ID" "$$LOCAL_DOMAIN" \
			"$$KC_AUTHORITY" \
			"$$API_ENDPOINT" > ../$(APP_COGNITO)/.env
	@echo "Generated: $(APP_COGNITO)/.env"

app-kc-env: ## [app] app-keycloak/.env を terraform output から自動生成
	@cd $(TF_KC_DIR) && \
		AUTHORITY=$$(terraform output -raw keycloak_oidc_issuer); \
		API_ENDPOINT=$$(cd ../../$(TF_INFRA_DIR) && terraform output -raw api_gateway_url); \
		printf "VITE_KEYCLOAK_AUTHORITY=%s\nVITE_KEYCLOAK_CLIENT_ID=auth-poc-spa\nVITE_REDIRECT_URI=http://localhost:5174/callback\nVITE_POST_LOGOUT_URI=http://localhost:5174/\n\nVITE_API_ENDPOINT=%s\n" \
			"$$AUTHORITY" "$$API_ENDPOINT" > ../../$(APP_KEYCLOAK)/.env
	@echo "Generated: $(APP_KEYCLOAK)/.env"

app-dev: ## [app] Cognito版 SPA 開発サーバー起動 (port 5173)
	cd $(APP_COGNITO) && npm run dev

app-kc-dev: ## [app] Keycloak版 SPA 開発サーバー起動 (port 5174)
	cd $(APP_KEYCLOAK) && npm run dev

app-sso-dev: ## [app] SSO 検証用ピア SPA 起動 (port 5175) - Keycloak の cross-client SSO 検証
	cd $(APP_SSO_PEER) && npm run dev

# ==============================================================================
# [cognito-*] Cognito ユーザー管理
# ==============================================================================

cognito-create-test-users: ## [cognito] テストユーザー作成（eve@partner.com on Local Cognito）
	@LOCAL_POOL=$$(cd $(TF_INFRA_DIR) && terraform output -raw local_cognito_user_pool_id); \
	aws cognito-idp admin-create-user \
		--user-pool-id $$LOCAL_POOL \
		--username eve@partner.com \
		--user-attributes Name=email,Value=eve@partner.com Name=email_verified,Value=true Name=custom:tenant_id,Value=partner-co Name=custom:roles,Value=employee \
		--temporary-password "TempPass1!" \
		--message-action SUPPRESS \
		--region $(AWS_REGION) --no-cli-pager 2>&1 | head -3; \
	aws cognito-idp admin-set-user-password \
		--user-pool-id $$LOCAL_POOL \
		--username eve@partner.com \
		--password "TestPass1!" \
		--permanent \
		--region $(AWS_REGION) --no-cli-pager; \
	aws cognito-idp admin-add-user-to-group \
		--user-pool-id $$LOCAL_POOL \
		--username eve@partner.com \
		--group-name partner-users \
		--region $(AWS_REGION) --no-cli-pager
	@echo "Created eve@partner.com / TestPass1! (partner-co / employee)"
	@echo ""
	@echo "alice/bob/carol/dave は Auth0 ダッシュボードで作成してください:"
	@echo "  see doc/common/auth0-setup-claims.md"

cognito-list-users: ## [cognito] Central + Local Cognito のユーザー一覧
	@echo "=== Central Cognito ==="
	@CENTRAL_POOL=$$(cd $(TF_INFRA_DIR) && terraform output -raw cognito_user_pool_id); \
	aws cognito-idp list-users --user-pool-id $$CENTRAL_POOL --region $(AWS_REGION) \
		--query 'Users[*].{Username:Username,Email:Attributes[?Name==`email`].Value|[0],Tenant:Attributes[?Name==`custom:tenant_id`].Value|[0],Roles:Attributes[?Name==`custom:roles`].Value|[0]}' \
		--output table --no-cli-pager
	@echo ""
	@echo "=== Local Cognito ==="
	@LOCAL_POOL=$$(cd $(TF_INFRA_DIR) && terraform output -raw local_cognito_user_pool_id); \
	aws cognito-idp list-users --user-pool-id $$LOCAL_POOL --region $(AWS_REGION) \
		--query 'Users[*].{Username:Username,Email:Attributes[?Name==`email`].Value|[0],Tenant:Attributes[?Name==`custom:tenant_id`].Value|[0],Roles:Attributes[?Name==`custom:roles`].Value|[0]}' \
		--output table --no-cli-pager

keycloak-users-guide: ## [keycloak] Keycloak テストユーザー作成ガイドを表示
	@echo "Keycloak のテストユーザーは Admin Console から作成してください:"
	@echo ""
	@echo "  Admin URL:"
	@cd $(TF_KC_DIR) && terraform output -raw keycloak_admin_url 2>/dev/null
	@echo ""
	@echo "  手順書: doc/keycloak/claim-mapping-setup.md の §4"
	@echo ""
	@echo "  作成するユーザー:"
	@echo "    alice-kc / bob-kc / carol-kc / dave-kc"

# ==============================================================================
# [logs-*] CloudWatch Logs
# ==============================================================================

logs-authorizer: ## [logs] Lambda Authorizer (LOG_SINCE=10m)
	aws logs tail /aws/lambda/auth-poc-authorizer --since $(LOG_SINCE) --follow --region $(AWS_REGION) --no-cli-pager

logs-backend: ## [logs] Backend Lambda
	aws logs tail /aws/lambda/auth-poc-backend --since $(LOG_SINCE) --follow --region $(AWS_REGION) --no-cli-pager

logs-pre-token: ## [logs] Pre Token Generation Lambda
	aws logs tail /aws/lambda/auth-poc-pre-token --since $(LOG_SINCE) --follow --region $(AWS_REGION) --no-cli-pager

logs-keycloak: kc-logs ## [logs] Keycloak ECS ログ（kc-logs のエイリアス）

# ==============================================================================
# [ip-*] ALB への IP 許可リスト管理
# ==============================================================================

KC_ADMIN_SG := $(shell aws ec2 describe-security-groups --filters "Name=group-name,Values=auth-poc-kc-alb-admin-sg" --region $(AWS_REGION) --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)

ip-show: ## [ip] Keycloak Admin ALB / Public ALB(L7) の許可IP一覧
	@echo "=== Admin ALB SG (auth-poc-kc-alb-admin-sg) ==="
	@aws ec2 describe-security-groups --group-ids $(KC_ADMIN_SG) --region $(AWS_REGION) \
		--query 'SecurityGroups[0].IpPermissions[*].{from:FromPort,cidrs:IpRanges[*].CidrIp}' \
		--output json --no-cli-pager
	@echo ""
	@echo "=== Public ALB Listener Rule(L7) - browser_endpoints_ip_restricted の許可CIDR ==="
	@RULE_ARN=$$(aws elbv2 describe-rules --listener-arn $$(aws elbv2 describe-listeners --load-balancer-arn $$(aws elbv2 describe-load-balancers --names auth-poc-kc-alb --region $(AWS_REGION) --query 'LoadBalancers[0].LoadBalancerArn' --output text) --region $(AWS_REGION) --query 'Listeners[0].ListenerArn' --output text) --region $(AWS_REGION) --query 'Rules[?Priority==`200`].RuleArn' --output text); \
	aws elbv2 describe-rules --rule-arns $$RULE_ARN --region $(AWS_REGION) \
		--query 'Rules[0].Conditions[?Field==`source-ip`].SourceIpConfig.Values' --output json
	@echo ""
	@echo "=== terraform.tfvars: allowed_cidr_blocks ==="
	@grep allowed_cidr_blocks $(TF_KC_DIR)/terraform.tfvars

ip-add: ## [ip] Admin ALB(SG) に IP を追加 (IP=x.x.x.x)
	@if [ -z "$(IP)" ]; then echo "Usage: make ip-add IP=x.x.x.x"; exit 1; fi
	aws ec2 authorize-security-group-ingress \
		--group-id $(KC_ADMIN_SG) \
		--protocol tcp --port 80 --cidr $(IP)/32 \
		--region $(AWS_REGION) --no-cli-pager
	@echo "Added $(IP)/32 to Admin ALB"

ip-add-provider: ## [ip] 現在の接続元プロバイダ IP を Admin ALB(SG) に追加
	@MY_IP=$$(curl -s https://checkip.amazonaws.com | tr -d '\n'); \
	echo "Your IP: $$MY_IP"; \
	aws ec2 authorize-security-group-ingress \
		--group-id $(KC_ADMIN_SG) \
		--protocol tcp --port 80 --cidr $$MY_IP/32 \
		--region $(AWS_REGION) --no-cli-pager 2>&1 | head -3

ip-add-public: ## [ip] Public ALB(L7) のブラウザ用許可CIDRに追加 (CIDR=x.x.x.x/16 等) → terraform apply で反映
	@if [ -z "$(CIDR)" ]; then echo "Usage: make ip-add-public CIDR=1.75.0.0/16"; exit 1; fi
	@python3 -c "\
	import re; \
	f=open('$(TF_KC_DIR)/terraform.tfvars'); t=f.read(); f.close(); \
	m=re.search(r'allowed_cidr_blocks\s*=\s*\[(.*?)\]', t); \
	current=m.group(1) if m else ''; \
	new_cidr='\"$(CIDR)\"'; \
	(print('既に登録済み: $(CIDR)') or exit(0)) if new_cidr in current else None; \
	updated=current.rstrip().rstrip(',')+', '+new_cidr if current.strip() else new_cidr; \
	t=t.replace(m.group(0), 'allowed_cidr_blocks     = ['+updated+']'); \
	f=open('$(TF_KC_DIR)/terraform.tfvars','w'); f.write(t); f.close(); \
	print('Updated tfvars'); \
	"
	@grep allowed_cidr_blocks $(TF_KC_DIR)/terraform.tfvars
	@echo ""
	@echo "Run 'make tf-apply-kc' to apply"

ip-add-public-provider: ## [ip] 接続元プロバイダの /16 を Public ALB(L7) 許可リストに追加
	@MY_IP=$$(curl -s https://checkip.amazonaws.com | tr -d '\n'); \
	OCTETS=$$(echo $$MY_IP | awk -F. '{print $$1"."$$2".0.0/16"}'); \
	echo "Your IP: $$MY_IP → adding $$OCTETS"; \
	$(MAKE) ip-add-public CIDR=$$OCTETS

ip-set-my-ip: ## [ip] tfvars の allowed_cidr_blocks を現在の自IPで上書き (terraform apply 後に反映)
	@MY_IP=$$(curl -s https://checkip.amazonaws.com | tr -d '\n'); \
	echo "Updating terraform.tfvars with: $$MY_IP/32"; \
	sed -i "s|^allowed_cidr_blocks.*=.*|allowed_cidr_blocks     = [\"$$MY_IP/32\"]|" $(TF_KC_DIR)/terraform.tfvars; \
	grep allowed_cidr_blocks $(TF_KC_DIR)/terraform.tfvars
	@echo "Run 'make tf-apply-kc' to apply"

ip-clear: ## [ip] Admin ALB のIP許可をすべて削除（危険: Admin Console にアクセス不可になる）
	@aws ec2 describe-security-groups --group-ids $(KC_ADMIN_SG) --region $(AWS_REGION) \
		--query 'SecurityGroups[0].IpPermissions' --output json | \
	jq -r '.[].IpRanges[].CidrIp' | \
	while read cidr; do \
		aws ec2 revoke-security-group-ingress --group-id $(KC_ADMIN_SG) --protocol tcp --port 80 --cidr $$cidr --region $(AWS_REGION) --no-cli-pager 2>&1 | head -1; \
	done
	@echo "Cleared all IPs from Admin ALB"

# ==============================================================================
# [status] 全体ステータス
# ==============================================================================

status: ## [status] 環境全体の状態を表示
	@echo "==============================================="
	@echo " AWS 認証基盤 PoC - 環境ステータス"
	@echo "==============================================="
	@echo ""
	@echo "--- AWS 認証 ---"
	@aws sts get-caller-identity --query '{Account:Account,Arn:Arn}' --output table --no-cli-pager 2>&1 || echo "SSO 未ログイン (make sso-login)"
	@echo ""
	@echo "--- 東京インフラ ---"
	@cd $(TF_INFRA_DIR) && terraform output -raw api_gateway_url 2>/dev/null && echo "" || echo "未デプロイ"
	@echo ""
	@echo "--- Keycloak ---"
	@cd $(TF_KC_DIR) && terraform output -raw keycloak_public_url 2>/dev/null && echo "" || echo "未デプロイ"
	@cd $(TF_KC_DIR) && terraform output -raw keycloak_admin_url 2>/dev/null && echo "" || true

sso-login: ## [util] AWS SSO ログイン
	aws sso login

# ==============================================================================
# [clean] クリーンアップ
# ==============================================================================

clean: ## [util] ビルド成果物を削除
	rm -rf $(LAMBDA_AUTHORIZER)/build $(LAMBDA_AUTHORIZER)/package.zip $(LAMBDA_AUTHORIZER)/.venv
	rm -f $(LAMBDA_BACKEND)/package.zip
	rm -f $(LAMBDA_PRE_TOKEN)/package.zip
	rm -f $(TF_INFRA_DIR)/tfplan $(TF_DR_DIR)/tfplan $(TF_KC_DIR)/tfplan

# ==============================================================================
# ヘルプ
# ==============================================================================

help: ## このヘルプを表示
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
