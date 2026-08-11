import logging
from typing import Dict, Any

class PromptRegistry:
    def __init__(self):
        self.templates: Dict[str, str] = {}
        self.system_prompts: Dict[str, str] = {}

    def register(self, prompt_id: str, template: str, system_prompt: str = ""):
        self.templates[prompt_id] = template
        if system_prompt:
            self.system_prompts[prompt_id] = system_prompt
        logging.info(f"Registered prompt template: {prompt_id}")

    def get_template(self, prompt_id: str) -> str:
        return self.templates.get(prompt_id, "")

    def get_system_prompt(self, prompt_id: str) -> str:
        return self.system_prompts.get(prompt_id, "")

    def render(self, prompt_id: str, context: Dict[str, Any]) -> str:
        template = self.get_template(prompt_id)
        if not template:
            # If not registered, treat prompt_id itself as the prompt or return empty
            return str(context.get("prompt", prompt_id))
        
        try:
            return template.format(**context)
        except KeyError as e:
            logging.error(f"Failed to render prompt '{prompt_id}': Missing context variable {e}")
            raise ValueError(f"Missing context variable: {e}")
