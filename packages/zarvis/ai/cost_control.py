import logging
from typing import Dict, Any

class AICostController:
    def __init__(self, daily_budget_limit: float = 10.0):
        self.daily_budget = daily_budget_limit
        self.current_spent = 0.0
        
        # Standard cost per call mapping (mock rates for standard tokens)
        self.rates = {
            "claude": 0.015,
            "openai": 0.010,
            "gemini": 0.005,
            "deepseek": 0.002,
            "ollama": 0.000 # Local model is free
        }

    def check_budget_exceeded(self) -> bool:
        if self.current_spent >= self.daily_budget:
            logging.warning(f"AI Budget exceeded! Spent: ${self.current_spent:.4f} / Limit: ${self.daily_budget:.2f}")
            return True
        return False

    def track_call(self, provider: str, cost: float = 0.0):
        # If no cost provided, look up rate or use standard generic cost
        if cost == 0.0:
            cost = self.rates.get(provider, 0.005)
            
        self.current_spent += cost
        logging.info(f"AI Spent: +${cost:.4f} via {provider} | Total Daily: ${self.current_spent:.4f}")

    def reset_budget(self):
        self.current_spent = 0.0
