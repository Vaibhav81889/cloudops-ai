output "api_url" {
  description = "Local URL for the Terraform-managed CloudOps API"
  value       = "http://127.0.0.1:${var.host_port}/docs"
}

output "container_id" {
  value = docker_container.api.id
}
