# ==============================================================================
# Stage A-2: ECS Service Application Auto Scaling
# - 初期 desired_count は Terraform で設定（var.keycloak_desired_count）
# - その後の動的調整は Application Auto Scaling に委譲
# - lifecycle.ignore_changes=[desired_count] と組み合わせ、Terraform は介入しない
# ==============================================================================

resource "aws_appautoscaling_target" "keycloak" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.keycloak.name}/${aws_ecs_service.keycloak.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.keycloak_autoscale_min
  max_capacity       = var.keycloak_autoscale_max
}

# CPU 使用率ベースのターゲット追跡スケーリング
# 認証基盤は CPU バウンド（JWT 署名・JIT プロビジョニング・パスワードハッシュ計算）のため CPU 指標で十分
resource "aws_appautoscaling_policy" "keycloak_cpu" {
  name               = "${local.prefix}-cpu-tracking"
  service_namespace  = aws_appautoscaling_target.keycloak.service_namespace
  resource_id        = aws_appautoscaling_target.keycloak.resource_id
  scalable_dimension = aws_appautoscaling_target.keycloak.scalable_dimension
  policy_type        = "TargetTrackingScaling"

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70 # 平均 CPU 70% 超過でスケールアウト
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# メモリ使用率ベース（CPU と並列適用、どちらかが閾値超で発火）
# Keycloak は Infinispan キャッシュ・JVM ヒープがメモリ消費の主因
resource "aws_appautoscaling_policy" "keycloak_memory" {
  name               = "${local.prefix}-memory-tracking"
  service_namespace  = aws_appautoscaling_target.keycloak.service_namespace
  resource_id        = aws_appautoscaling_target.keycloak.resource_id
  scalable_dimension = aws_appautoscaling_target.keycloak.scalable_dimension
  policy_type        = "TargetTrackingScaling"

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 75
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
