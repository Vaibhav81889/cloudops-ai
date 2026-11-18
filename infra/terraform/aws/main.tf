terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Dynamically look up the latest official Ubuntu 24.04 LTS AMI from Canonical
data "aws_ami" "ubuntu_24_04" {
  most_recent = true
  owners      = ["099720109477"] # Official Canonical AWS account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_key_pair" "deploy" {
  key_name   = "cloudops-ai-deploy-key"
  public_key = var.ssh_public_key
}

# Cloud equivalent of your Lesson 18 UFW firewall (inbound SSH only from your IP)
resource "aws_security_group" "cloudops_sg" {
  name        = "cloudops-ai-server-sg"
  description = "Allow SSH from admin IP only; access app/Grafana via SSH tunnel"

  ingress {
    description = "SSH from admin workstation only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    description = "Outbound internet for apt updates and GHCR image pulls"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "cloudops-ai-sg"
    Project = "cloudops-ai"
  }
}

resource "aws_instance" "cloudops_server" {
  ami                         = data.aws_ami.ubuntu_24_04.id
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.deploy.key_name
  vpc_security_group_ids      = [aws_security_group.cloudops_sg.id]
  associate_public_ip_address = true

  # Enforce IMDSv2 to protect instance metadata from SSRF attacks
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  # Encrypted root volume matching our VM disk setup
  root_block_device {
    volume_size = 15
    volume_type = "gp3"
    encrypted   = true
  }

  # Reuse your sanitized cloud-init template from Lesson 18
  user_data = file("${path.module}/../../vm/user-data.example.yaml")

  tags = {
    Name    = "cloudops-ai-server"
    Project = "cloudops-ai"
  }
}
