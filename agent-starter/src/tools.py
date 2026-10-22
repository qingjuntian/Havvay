"""Example tools the agent may call. Implement validation and sandboxing for any real tool.
"""
import ast
import math
import re
import os

try:
    from tavily import TavilyClient
except ImportError:  # Keep non-search tools available without optional search dependencies.
    TavilyClient = None



def _evaluate_expression(expression: str) -> float:
    if len(expression) > 200:
        raise ValueError("expression is too long")

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if not math.isfinite(node.value):
                raise ValueError("number must be finite")
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return +evaluate(node.operand) if isinstance(node.op, ast.UAdd) else -evaluate(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if abs(right) > 100:
                raise ValueError("exponent is too large")
            return left ** right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt":
            if len(node.args) != 1 or node.keywords:
                raise ValueError("sqrt accepts one positional argument")
            return math.sqrt(evaluate(node.args[0]))
        raise ValueError("unsupported expression")

    result = evaluate(tree.body)
    if not math.isfinite(result):
        raise ValueError("result must be finite")
    return result

class Tools:
    def calc(self, prompt: str) -> str:
        m = re.search(r"calculate\s+(.*)", prompt, re.I)
        expr = m.group(1) if m else ""
        try:
            value = _evaluate_expression(expr)
            return f"Calculation result: {value}"
        except Exception as e:
            return f"Calculation failed: {e}"

    def search_web(self, query: str) -> str:
        query = query.strip()
        if not query:
            return "Web search failed: query cannot be empty."

        tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not tavily_api_key:
            return "Web search is unavailable: set TAVILY_API_KEY to enable Tavily search."
        if TavilyClient is None:
            return "Web search is unavailable: install tavily-python to enable Tavily search."

        try:
            response = TavilyClient(api_key=tavily_api_key).search(
                query=query,
                max_results=5,
                search_depth="basic",
            )
        except Exception as exc:
            return f"Web search failed: {exc}"

        lines = [f"Search results for: {query}"]
        answer = response.get("answer")
        if answer:
            lines.extend(["", f"Answer: {answer}"])

        results = response.get("results", [])
        for index, result in enumerate(results[:5], start=1):
            title = result.get("title") or "Untitled result"
            url = result.get("url") or ""
            content = (result.get("content") or "").strip()
            if len(content) > 500:
                content = content[:497].rstrip() + "..."
            lines.extend(["", f"{index}. {title}"])
            if url:
                lines.append(f"URL: {url}")
            if content:
                lines.append(content)

        if not results and not answer:
            lines.extend(["", "No results found."])
        return "\n".join(lines)
