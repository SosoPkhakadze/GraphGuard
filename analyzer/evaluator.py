"""
Send both prompts to Claude and return the responses side by side.
Requires ANTHROPIC_API_KEY environment variable (or pass api_key explicitly).
"""

import os
import anthropic

MODEL = "claude-sonnet-4-6"


class Evaluator:
    def __init__(self, api_key=None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def evaluate(self, prompt_diff_only, prompt_with_graph):
        """
        Run both prompts and return a dict with both responses.
        Calls are made sequentially to keep rate limiting simple.
        """
        print("  [A] Querying Claude with diff only...")
        response_a = self._query(prompt_diff_only)

        print("  [B] Querying Claude with diff + call graph...")
        response_b = self._query(prompt_with_graph)

        return {
            "diff_only": response_a,
            "diff_with_graph": response_b,
        }

    def _query(self, prompt):
        msg = self.client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
