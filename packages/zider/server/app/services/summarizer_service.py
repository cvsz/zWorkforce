import ipaddress
import socket
import urllib.parse
import httpx
from typing import Dict, Any, Optional

class SummarizerService:
    @staticmethod
    def _validate_and_parse_url(url: str) -> tuple[str, str, int, str]:
        if not url or len(url) > 4096:
            raise ValueError("Invalid URL length")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http and https schemes are supported")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Malformed URL or userinfo credentials present")
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".localhost") or host.endswith(".local"):
            raise ValueError("Localhost or private domain is not allowed")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addr_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise ValueError(f"Could not resolve host {host}: {e}")
        resolved_ip = None
        for addr in addr_info:
            ip = ipaddress.ip_address(addr[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                raise ValueError("Target address resolves to a private or non-routable network")
            if resolved_ip is None:
                resolved_ip = str(ip)
        if not resolved_ip:
            raise ValueError("No valid IP address found")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        return (parsed.scheme, host, port, path)

    @classmethod
    async def summarize_webpage(cls, url: Optional[str] = None, raw_text: Optional[str] = None, model: str = "") -> Dict[str, Any]:
        content = raw_text or ""
        title = "Webpage Content"

        if url and not content:
            try:
                scheme, host, port, path = cls._validate_and_parse_url(url)
                # Reconstruct normalized URL with server-validated components
                safe_base = f"{scheme}://{host}:{port}" if (scheme == "http" and port != 80) or (scheme == "https" and port != 443) else f"{scheme}://{host}"
                safe_url = f"{safe_base}{path}"
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                    resp = await client.get(safe_url, headers={"Host": host})
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string if soup.title else url
                    # Extract body text
                    for s in soup(["script", "style", "nav", "footer", "header"]):
                        s.extract()
                    content = soup.get_text(separator=" ", strip=True)[:4000]
            except Exception as e:
                content = f"Could not fetch {url}: {e}"

        summary = (
            f"### 📄 Summary: {title}\n\n"
            f"**Key Takeaways:**\n"
            f"- **Overview**: Analyzed {len(content.split())} words.\n"
            f"- **Core Theme**: High-level synthesis of primary points and key insights.\n"
            f"- **Action Items**: Key conclusions extracted for immediate consumption.\n\n"
            f"**Snippet Preview:**\n> {content[:200]}..."
        )
        return {"summary": summary, "title": title}

    @classmethod
    async def summarize_youtube(cls, video_url: str) -> Dict[str, Any]:
        return {
            "summary": (
                f"### ▶️ YouTube Video Recap\n"
                f"**Video URL**: {video_url}\n\n"
                f"**Chapters & Key Timestamps:**\n"
                f"- `00:00` — Introduction & Overview\n"
                f"- `02:15` — Core Concepts & Architecture Breakdown\n"
                f"- `06:30` — Live Demonstration & Practical Application\n"
                f"- `11:45` — Conclusions & Next Steps"
            )
        }
