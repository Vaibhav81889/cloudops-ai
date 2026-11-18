variable "aws_region" {
  description = "AWS region (Mumbai by default)"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance size (t3.micro is Free Tier eligible)"
  type        = string
  default     = "t3.micro"
}

variable "ssh_allowed_cidr" {
  description = "Single admin IP in CIDR format (e.g. 203.0.113.10/32). Never use 0.0.0.0/0."
  type        = string

  validation {
    condition     = var.ssh_allowed_cidr != "0.0.0.0/0"
    error_message = "Refusing to open SSH port 22 to the entire internet (0.0.0.0/0)."
  }
}

variable "ssh_public_key" {
  description = "Ed25519 SSH public key string for EC2 login"
  type        = string
}
