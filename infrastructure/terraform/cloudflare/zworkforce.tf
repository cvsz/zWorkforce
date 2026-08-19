# ==============================================================================
# zWorkforce & ZSP Studio Cloudflare Stack Specification (*.zeaz.dev)
# ==============================================================================

variable "zwf_hostname" {
  type        = string
  default     = "zwf.zeaz.dev"
  description = "Public hostname for the zWorkforce Enterprise API & Orchestration Control Plane."

  validation {
    condition     = endswith(lower(var.zwf_hostname), ".${lower(var.zone_name)}")
    error_message = "zwf_hostname must be a subdomain of zone_name."
  }
}

variable "zwf_origin" {
  type        = string
  default     = "http://127.0.0.1:9570"
  description = "Loopback origin published by the zWorkforce API service."

  validation {
    condition     = can(regex("^http://127\\.0\\.0\\.1:[0-9]+$", var.zwf_origin))
    error_message = "zwf_origin must use a loopback address."
  }
}

variable "studio_hostname" {
  type        = string
  default     = "studio.zeaz.dev"
  description = "Public hostname for the ZSP Studio AI Content & HyperFrames Platform."

  validation {
    condition     = endswith(lower(var.studio_hostname), ".${lower(var.zone_name)}")
    error_message = "studio_hostname must be a subdomain of zone_name."
  }
}

variable "studio_origin" {
  type        = string
  default     = "http://127.0.0.1:3005"
  description = "Loopback origin published by the ZSP-AITool Studio Next.js application."

  validation {
    condition     = can(regex("^http://127\\.0\\.0\\.1:[0-9]+$", var.studio_origin))
    error_message = "studio_origin must use a loopback address."
  }
}

variable "zarvis_hostname" {
  type        = string
  default     = "zarvis.zeaz.dev"
  description = "Public hostname for the Z.A.R.V.I.S. Autonomous Voice & Executive Assistant Gateway."

  validation {
    condition     = endswith(lower(var.zarvis_hostname), ".${lower(var.zone_name)}")
    error_message = "zarvis_hostname must be a subdomain of zone_name."
  }
}

variable "zarvis_origin" {
  type        = string
  default     = "http://127.0.0.1:9570"
  description = "Loopback origin published for Z.A.R.V.I.S. (zWorkforce API & Voice Gateway)."

  validation {
    condition     = can(regex("^http://127\\.0\\.0\\.1:[0-9]+$", var.zarvis_origin))
    error_message = "zarvis_origin must use a loopback address."
  }
}

variable "zider_hostname" {
  type        = string
  default     = "zider.zeaz.dev"
  description = "Public hostname for zider AI Sidebar, ChatPDF & Multi-Model Workspace."

  validation {
    condition     = endswith(lower(var.zider_hostname), ".${lower(var.zone_name)}")
    error_message = "zider_hostname must be a subdomain of zone_name."
  }
}

variable "zider_origin" {
  type        = string
  default     = "http://127.0.0.1:8085"
  description = "Loopback origin published by the zider BFF FastAPI / Node gateway."

  validation {
    condition     = can(regex("^http://127\\.0\\.0\\.1:[0-9]+$", var.zider_origin))
    error_message = "zider_origin must use a loopback address."
  }
}

# Canonical zWorkforce-family ingress. Keeping the host/origin pairs next to the
# DNS declarations prevents the local cloudflared manifest and managed tunnel
# configuration from silently diverging.
locals {
  zworkforce_ingress = [
    { hostname = var.zwf_hostname, service = var.zwf_origin },
    { hostname = var.studio_hostname, service = var.studio_origin },
    { hostname = var.zarvis_hostname, service = var.zarvis_origin },
    { hostname = var.zider_hostname, service = var.zider_origin },
  ]
}

resource "cloudflare_dns_record" "zwf" {
  zone_id = var.cloudflare_zone_id
  name    = var.zwf_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "zWorkforce Control Plane via Cloudflare Tunnel"
}

resource "cloudflare_dns_record" "studio" {
  zone_id = var.cloudflare_zone_id
  name    = var.studio_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "ZSP-AITool Studio via Cloudflare Tunnel"
}

resource "cloudflare_dns_record" "zarvis" {
  zone_id = var.cloudflare_zone_id
  name    = var.zarvis_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "Z.A.R.V.I.S. Autonomous Voice Assistant via Cloudflare Tunnel"
}

resource "cloudflare_dns_record" "zider" {
  zone_id = var.cloudflare_zone_id
  name    = var.zider_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "zider AI Browser Sidebar & Multi-Model Workspace via Cloudflare Tunnel"
}

output "zwf_url" {
  value       = "https://${var.zwf_hostname}"
  description = "Public zWorkforce Control Plane URL."
}

output "studio_url" {
  value       = "https://${var.studio_hostname}"
  description = "Public ZSP-AITool Studio URL."
}

output "zarvis_url" {
  value       = "https://${var.zarvis_hostname}"
  description = "Public Z.A.R.V.I.S. Autonomous Voice Assistant URL."
}

output "zider_url" {
  value       = "https://${var.zider_hostname}"
  description = "Public zider AI Sidebar & Workspace URL."
}
