variable "image_tag" {
  description = "Pinned GHCR image tag for CloudOps AI"
  type        = string
  default     = "sha-7256243"
}

variable "host_port" {
  description = "Localhost port mapped to FastAPI (8081 avoids clashing with your SSH tunnel on 8000)"
  type        = number
  default     = 8081
}
