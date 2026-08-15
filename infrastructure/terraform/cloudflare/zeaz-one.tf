variable "enable_zeaz_one" {
  type        = bool
  default     = false
  description = "Create ZEAZ One website and support tunnel DNS records and include their ingress routes."
}

variable "enable_zeaz_one_api_route" {
  type        = bool
  default     = false
  description = "Create only the ZEAZ One product path on the existing shared api.zeaz.dev hostname."
}

variable "zeaz_one_hostname" {
  type        = string
  default     = "one.zeaz.dev"
  description = "Primary public hostname for ZEAZ One."

  validation {
    condition     = endswith(lower(var.zeaz_one_hostname), ".${lower(var.zone_name)}")
    error_message = "zeaz_one_hostname must be a subdomain of zone_name."
  }
}

variable "zeaz_one_origin" {
  type        = string
  default     = "http://127.0.0.1:18081"
  description = "Loopback-only ZEAZ One website origin."

  validation {
    condition     = var.zeaz_one_origin == "http://127.0.0.1:18081"
    error_message = "zeaz_one_origin must use the reviewed loopback origin at http://127.0.0.1:18081."
  }
}

variable "zeaz_one_api_hostname" {
  type        = string
  default     = "api.zeaz.dev"
  description = "Existing shared API hostname receiving only the ZEAZ One path-specific Worker route."

  validation {
    condition     = lower(var.zeaz_one_api_hostname) == "api.${lower(var.zone_name)}"
    error_message = "zeaz_one_api_hostname must be the shared api hostname of zone_name."
  }
}

variable "zeaz_one_api_origin" {
  type        = string
  default     = "http://127.0.0.1:18084"
  description = "Loopback-only API parity and health origin; it is not published as the api.zeaz.dev DNS target."

  validation {
    condition     = var.zeaz_one_api_origin == "http://127.0.0.1:18084"
    error_message = "zeaz_one_api_origin must use the reviewed loopback origin at http://127.0.0.1:18084."
  }
}

variable "zeaz_one_support_hostname" {
  type        = string
  default     = "support.zeaz.dev"
  description = "Public hostname for ZEAZ One support."

  validation {
    condition     = endswith(lower(var.zeaz_one_support_hostname), ".${lower(var.zone_name)}")
    error_message = "zeaz_one_support_hostname must be a subdomain of zone_name."
  }
}

variable "zeaz_one_support_origin" {
  type        = string
  default     = "http://127.0.0.1:18083"
  description = "Loopback-only ZEAZ One support origin."

  validation {
    condition     = var.zeaz_one_support_origin == "http://127.0.0.1:18083"
    error_message = "zeaz_one_support_origin must use the reviewed loopback origin at http://127.0.0.1:18083."
  }
}

locals {
  zeaz_one_ingress = var.enable_zeaz_one ? [
    { hostname = var.zeaz_one_hostname, service = var.zeaz_one_origin },
    { hostname = var.zeaz_one_support_hostname, service = var.zeaz_one_support_origin },
  ] : []
}

resource "cloudflare_dns_record" "zeaz_one" {
  count   = var.enable_zeaz_one ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.zeaz_one_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "ZEAZ One website via Cloudflare Tunnel"
}

resource "cloudflare_dns_record" "zeaz_one_support" {
  count   = var.enable_zeaz_one ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.zeaz_one_support_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "ZEAZ One support via Cloudflare Tunnel"
}

resource "cloudflare_workers_script" "zeaz_one_api" {
  count              = var.enable_zeaz_one && var.enable_zeaz_one_api_route ? 1 : 0
  account_id         = var.cloudflare_account_id
  script_name        = "zeaz-one-product-api"
  compatibility_date = "2026-08-07"
  main_module        = "zeaz-one-product-api.js"
  content_file       = "${path.module}/workers/zeaz-one-product-api.js"
  content_sha256     = filesha256("${path.module}/workers/zeaz-one-product-api.js")
}

resource "cloudflare_workers_route" "zeaz_one_api" {
  count   = var.enable_zeaz_one && var.enable_zeaz_one_api_route ? 1 : 0
  zone_id = var.cloudflare_zone_id
  pattern = "${var.zeaz_one_api_hostname}/v1/products/zeaz-one*"
  script  = cloudflare_workers_script.zeaz_one_api[0].script_name
}

output "zeaz_one_url" {
  value       = "https://${var.zeaz_one_hostname}"
  description = "Primary ZEAZ One product URL."
}

output "zeaz_one_api_url" {
  value       = "https://${var.zeaz_one_api_hostname}/v1/products/zeaz-one"
  description = "Path-specific ZEAZ One product API URL on the existing shared API hostname."
}

output "zeaz_one_support_url" {
  value       = "https://${var.zeaz_one_support_hostname}/zeaz-one"
  description = "ZEAZ One support URL."
}

output "zeaz_one_corporate_url" {
  value       = "https://www.${var.zone_name}/products/zeaz-one"
  description = "Canonical corporate ZEAZ One URL owned and deployed by cvsz/zeaz-platform."
}
