from typing import List, Dict, Any

class PromptLibraryService:
    """
    Categorized Prompt Library service for zider
    """
    _PROMPTS = [
        {
            "id": "code_refactor",
            "category": "Coding",
            "title": "Refactor & Clean Code",
            "icon": "💻",
            "template": "Refactor the following code to improve readability, performance, and adhere to clean architecture best practices. Provide before/after explanations:\n\n```\n{{code}}\n```"
        },
        {
            "id": "code_explain",
            "category": "Coding",
            "title": "Explain Complex Code",
            "icon": "🔍",
            "template": "Explain how this code works step-by-step. Highlight potential edge cases, complexity (Big-O), and architectural assumptions:\n\n```\n{{code}}\n```"
        },
        {
            "id": "code_unit_test",
            "category": "Coding",
            "title": "Generate Comprehensive Unit Tests",
            "icon": "🧪",
            "template": "Write comprehensive unit tests with 100% branch coverage including edge cases and mock fixtures for:\n\n```\n{{code}}\n```"
        },
        {
            "id": "write_cold_email",
            "category": "Writing",
            "title": "Persuasive Cold Email",
            "icon": "✉️",
            "template": "Draft a concise, compelling cold email to {{recipient}} highlighting value proposition for {{product/service}} with a clear, low-friction call-to-action."
        },
        {
            "id": "write_reply_context",
            "category": "Writing",
            "title": "Smart Contextual Reply",
            "icon": "💬",
            "template": "Draft a professional, clear, and cordial reply to the following message:\n\n\"{{message}}\""
        },
        {
            "id": "read_tldr",
            "category": "Reading",
            "title": "Executive TL;DR Summary",
            "icon": "📋",
            "template": "Generate an executive TL;DR summary in 3 bullet points followed by actionable takeaways from this text:\n\n\"{{text}}\""
        },
        {
            "id": "read_fact_check",
            "category": "Reading",
            "title": "Fact-Check & Logical Fallacy Audit",
            "icon": "⚖️",
            "template": "Audit the following argument for logical fallacies, unverified claims, and potential bias:\n\n\"{{text}}\""
        },
        {
            "id": "agent_dom_extract",
            "category": "Automation",
            "title": "Extract Structured Data Table",
            "icon": "📊",
            "template": "Inspect the active page elements and extract all visible items, pricing, ratings, and descriptions into a clean Markdown table."
        }
    ]

    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        return cls._PROMPTS

    @classmethod
    def get_by_category(cls, category: str) -> List[Dict[str, Any]]:
        return [p for p in cls._PROMPTS if p["category"].lower() == category.lower()]
