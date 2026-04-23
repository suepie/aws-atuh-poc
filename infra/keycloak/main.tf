terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}

locals {
  prefix = "${var.project_name}-kc"
}

# カスタム VPC は network.tf に定義（本番理想形）。
# VPC / サブネット / IGW / ルートテーブルは aws_vpc.main / aws_subnet.public / aws_subnet.private で参照。

data "aws_caller_identity" "current" {}

# plan/apply 実行時の自分のグローバルIPを自動取得
data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

locals {
  my_ip_cidr = "${chomp(data.http.my_ip.response_body)}/32"
}
