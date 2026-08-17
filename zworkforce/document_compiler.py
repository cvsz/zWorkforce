from __future__ import annotations

import csv
import io
import json
from typing import Any


class DocumentCompiler:
    """Compiles deep research findings into Marp slide decks, tabular CSVs, and SSML audio scripts."""

    @staticmethod
    def compile_marp_slides(title: str, sections: list[dict[str, Any]]) -> str:
        """Generates a Marp markdown presentation deck."""
        lines = [
            "---",
            "marp: true",
            "theme: gaia",
            "_class: lead",
            "paginate: true",
            "backgroundColor: #f5f5f5",
            "---",
            f"# {title}",
            "**Autonomous Deep Research Synthesis**",
            "",
        ]
        for idx, sec in enumerate(sections, 1):
            lines.extend([
                "---",
                f"## Slide {idx}: {sec.get('heading', 'Section')}",
                "",
                sec.get("content", "").strip(),
                "",
            ])
            if "citations" in sec and sec["citations"]:
                lines.append("**Key Sources:**")
                for c in sec["citations"]:
                    lines.append(f"- [{c.get('title', 'Source')}]({c.get('url', '#')})")
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def compile_tabular_csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
        """Generates a structured CSV report."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        return output.getvalue()

    @staticmethod
    def compile_ssml_audio_script(paragraphs: list[str], voice_name: str = "th-TH-Standard-A") -> str:
        """Generates SSML-tagged audio synthesis scripts."""
        script_parts = [
            "<speak>",
            f'  <voice name="{voice_name}">',
        ]
        for p in paragraphs:
            clean_text = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()
            if clean_text:
                script_parts.extend([
                    "    <p>",
                    f"      <s>{clean_text}</s>",
                    "      <break time=\"500ms\"/>",
                    "    </p>",
                ])
        script_parts.extend([
            "  </voice>",
            "</speak>",
        ])
        return "\n".join(script_parts)
