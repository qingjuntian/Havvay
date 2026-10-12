"""Example tools the agent may call. Implement validation and sandboxing for any real tool.
"""
import ast
import math
import re


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
        # placeholder for an external search tool
        return f"search results for: {query} (stub)"
