"""Example tools the agent may call. Implement validation and sandboxing for any real tool.
"""
import math

class Tools:
    def calc(self, prompt: str) -> str:
        # very naive: extract expression from the prompt
        import re
        m = re.search(r"calculate\s+(.*)", prompt, re.I)
        expr = m.group(1) if m else ""
        try:
            # restrict builtins
            value = eval(expr, {"__builtins__": {}}, {"sqrt": math.sqrt})
            return f"Calculation result: {value}"
        except Exception as e:
            return f"Calculation failed: {e}"

    def search_web(self, query: str) -> str:
        # placeholder for an external search tool
        return f"search results for: {query} (stub)"
