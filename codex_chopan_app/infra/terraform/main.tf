terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

module "network" {
  source = "./modules/network"
}

module "ecs" {
  source = "./modules/ecs"
  cluster_name = "chopan-cluster"
  vpc_id       = module.network.vpc_id
  subnets      = module.network.private_subnet_ids
}

variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}
