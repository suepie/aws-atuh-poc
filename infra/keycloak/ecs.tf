# ECS Cluster
resource "aws_ecs_cluster" "keycloak" {
  name = "${local.prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"  # PoCなのでコスト削減
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "keycloak" {
  name              = "/ecs/${local.prefix}"
  retention_in_days = 7
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${local.prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECR Pull権限
resource "aws_iam_role_policy" "ecr_pull" {
  name = "${local.prefix}-ecr-pull"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Role（ECS Exec 用のSSM権限付与先）
resource "aws_iam_role" "ecs_task" {
  name = "${local.prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_exec" {
  name = "${local.prefix}-ecs-exec"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "keycloak" {
  family                   = "${local.prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"  # 2 vCPU
  memory                   = "4096"  # 4 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "keycloak"
      image = "${aws_ecr_repository.keycloak.repository_url}:${var.keycloak_image_tag}"

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "KC_DB", value = "postgres" },
        { name = "KC_DB_URL", value = "jdbc:postgresql://${aws_db_instance.keycloak.endpoint}/keycloak" },
        { name = "KC_DB_USERNAME", value = "keycloak" },
        { name = "KC_DB_PASSWORD", value = var.db_password },
        { name = "KEYCLOAK_ADMIN", value = "admin" },
        { name = "KEYCLOAK_ADMIN_PASSWORD", value = var.keycloak_admin_password },
        { name = "KC_PROXY_HEADERS", value = "xforwarded" },
        { name = "KC_HTTP_ENABLED", value = "true" },
        { name = "KC_HOSTNAME_STRICT", value = "false" },
        { name = "KC_HEALTH_ENABLED", value = "true" },
      ]

      command = ["start-dev", "--import-realm"]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.keycloak.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "keycloak"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "exec 3<>/dev/tcp/localhost/9000 && echo -e 'GET /health/ready HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n' >&3 && cat <&3 | grep -q '\"status\":\"UP\"'"]
        interval    = 60
        timeout     = 30
        retries     = 10
        startPeriod = 180
      }
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "keycloak" {
  name            = "${local.prefix}-service"
  cluster         = aws_ecs_cluster.keycloak.id
  task_definition = aws_ecs_task_definition.keycloak.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true  # デフォルトVPC + ECR pull にパブリックIPが必要
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.keycloak.arn
    container_name   = "keycloak"
    container_port   = 8080
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.keycloak_admin.arn
    container_name   = "keycloak"
    container_port   = 8080
  }

  # デプロイ時の設定
  deployment_minimum_healthy_percent = 0    # PoCなのでダウンタイム許容
  deployment_maximum_percent         = 100

  # desired_countの手動変更を無視（停止/起動はCLIで行う）
  lifecycle {
    ignore_changes = [desired_count]
  }
}
