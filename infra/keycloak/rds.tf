# RDS Subnet Group
resource "aws_db_subnet_group" "keycloak" {
  name       = "${local.prefix}-db-subnet"
  subnet_ids = data.aws_subnets.default.ids
}

# RDS PostgreSQL（db.t4g.micro - 停止可能、最小コスト）
resource "aws_db_instance" "keycloak" {
  identifier     = "${local.prefix}-db"
  engine         = "postgres"
  engine_version = "16.4"
  instance_class = "db.t4g.micro"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "keycloak"
  username = "keycloak"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.keycloak.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = false  # PoCなのでシングルAZ（DRテスト時にtrueに変更可能）
  publicly_accessible = false
  skip_final_snapshot = true

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # 停止時の自動起動を防ぐ（7日後に自動起動はAWS仕様で回避不可）
  lifecycle {
    ignore_changes = [engine_version]
  }
}
