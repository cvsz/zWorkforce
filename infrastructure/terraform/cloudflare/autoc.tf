variable "autoc_hostname" {
  type        = string
  default     = "autoc.zeaz.dev"
  description = "Protected hostname for the autoc operations dashboard."

  validation {
    condition     = endswith(lower(var.autoc_hostname), ".${lower(var.zone_name)}")
    error_message = "autoc_hostname must be a subdomain of zone_name."
  }
}

variable "autoc_origin" {
  type        = string
  default     = "http://127.0.0.1:8001"
  description = "Loopback-only autoc gateway reached by cloudflared."

  validation {
    condition     = var.autoc_origin == "http://127.0.0.1:8001"
    error_message = "autoc_origin must use the local gateway at http://127.0.0.1:8001."
  }
}

resource "cloudflare_dns_record" "autoc" {
  zone_id = var.cloudflare_zone_id
  name    = var.autoc_hostname
  type    = "CNAME"
  content = local.tunnel_cname
  ttl     = 1
  proxied = true
  comment = "Protected autoc operations dashboard via Cloudflare Tunnel"
}

resource "cloudflare_zero_trust_access_application" "autoc" {
  account_id                 = var.cloudflare_account_id
  name                       = "Autoc Operations Dashboard"
  domain                     = var.autoc_hostname
  type                       = "self_hosted"
  session_duration           = "8h"
  app_launcher_visible       = false
  enable_binding_cookie      = true
  http_only_cookie_attribute = true

  policies = [{
    name       = "Approved autoc operators"
    precedence = 1
    decision   = "allow"
    include = [
      for email in sort(tolist(var.piewdash_access_allowed_emails)) :
      { email = { email = lower(email) } }
    ]
  }]
}

output "autoc_url" {
  value       = "https://${var.autoc_hostname}"
  description = "Protected autoc URL after DNS, tunnel ingress, and Cloudflare Access are active."
}
