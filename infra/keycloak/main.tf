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
      Project = "auth-poc"
      Phase   = "6-keycloak"
      ManagedBy = "terraform"
    }
  }
}

locals {
  prefix = "auth-poc-kc"
}

# 既存VPC情報の取得（デフォルトVPC使用）
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_caller_identity" "current" {}
