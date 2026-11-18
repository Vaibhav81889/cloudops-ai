terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_volume" "cloudops_data" {
  name = "cloudops-tf-data"
}

resource "docker_image" "cloudops" {
  name         = "ghcr.io/vaibhav81889/cloudops-ai:${var.image_tag}"
  keep_locally = true
}

resource "docker_container" "api" {
  name    = "cloudops-ai-tf-api"
  image   = docker_image.cloudops.image_id
  command = ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
  restart = "unless-stopped"

  ports {
    internal = 8000
    external = var.host_port
    ip       = "127.0.0.1"
  }

  volumes {
    volume_name    = docker_volume.cloudops_data.name
    container_path = "/data"
  }
}
