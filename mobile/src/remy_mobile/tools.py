"""Tools that make sense on a phone. Each returns text the model can repeat."""
import ast
import math
import operator
import urllib.parse
from datetime import datetime

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "exp": math.exp,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}
MAX_POWER = 1000


def get_time():
    return datetime.now().strftime("%H:%M")


def get_date():
    return datetime.now().strftime("%A, %B %d, %Y")


def _evaluate(node):
    """Same safe calculator as the desktop app: arithmetic only, never eval."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > MAX_POWER or abs(left) > 10 ** 6):
            raise ValueError("number too large")
        return _BINARY_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCTIONS and not node.keywords):
        return _FUNCTIONS[node.func.id](*[_evaluate(arg) for arg in node.args])
    raise ValueError("only arithmetic is allowed")


def calculate(expression):
    try:
        return str(_evaluate(ast.parse(str(expression), mode="eval")))
    except Exception as e:
        return f"Error: {e}"


def open_website(url, open_url):
    """Only web links: tel:, sms: or intent: could act without the user seeing it."""
    url = str(url).strip()
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme and scheme not in ("http", "https"):
        return "Error: only http and https links can be opened"
    if not scheme:
        url = "https://" + url
    open_url(url)
    return f"Opened {url} in the browser"


def search_web(query, open_url):
    open_url("https://duckduckgo.com/?q=" + urllib.parse.quote_plus(str(query)))
    return f"Opened search results for '{query}' in the browser. You can't read them, so tell the user they're on screen."


TOOL_FUNCTIONS = {
    "get_time": get_time,
    "get_date": get_date,
    "calculate": calculate,
    "open_website": open_website,
    "search_web": search_web,
}
NEEDS_BROWSER = {"open_website", "search_web"}


def _tool(name, description, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
        },
    }


TOOLS = [
    _tool("get_time", "Get the current time. Use when the user asks what time it is."),
    _tool("get_date", "Get today's date. Use when the user asks the date or the day."),
    _tool("calculate", "Calculate a math expression like '2 + 2' or 'sqrt(16)'.",
          {"expression": {"type": "string", "description": "The math expression"}}, ["expression"]),
    _tool("open_website", "Open a website in the phone's browser. ONLY when the user says 'open' a site or app with a website.",
          {"url": {"type": "string", "description": "Address, e.g. 'youtube.com'"}}, ["url"]),
    _tool("search_web", "Open a web search in the phone's browser. Use for 'search for X' or 'look up X'.",
          {"query": {"type": "string", "description": "What to search for"}}, ["query"]),
]


def run_tool(name, args, open_url):
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return f"Error: unknown tool {name}"
    try:
        if name in NEEDS_BROWSER:
            return str(function(**(args or {}), open_url=open_url))
        return str(function(**(args or {})))
    except Exception as e:
        return f"Error: {e}"
