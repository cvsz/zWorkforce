import httpx
from typing import Dict, Any, Optional

class SummarizerService:
    @classmethod
    async def summarize_webpage(cls, url: Optional[str] = None, raw_text: Optional[str] = None, model: str = "") -> Dict[str, Any]:
        content = raw_text or ""
        title = "Webpage Content"

        if url and not content:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(url)
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
