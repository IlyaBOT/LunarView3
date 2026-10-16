"""Small S-expression reader/writer for deterministic KiCad generation and audits."""
import json
import re

class Atom(str):
    pass

def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack = []
    root = None
    for t in tokens:
        if t == '(':
            a = []
            if stack:
                stack[-1].append(a)
            stack.append(a)
        elif t == ')':
            root = stack.pop()
        else:
            stack[-1].append(json.loads(t) if t.startswith('"') else Atom(t))
    return root

def dump(x):
    if isinstance(x, list):
        return '(' + ' '.join(dump(v) for v in x) + ')'
    if isinstance(x, Atom):
        return str(x)
    if isinstance(x, (int, float)):
        return f'{x:.6f}'.rstrip('0').rstrip('.') if isinstance(x, float) else str(x)
    return json.dumps(x, ensure_ascii=False)

def node(tag, *items):
    return [Atom(tag), *items]

def children(x, tag):
    return [c for c in x if isinstance(c, list) and c and c[0] == tag]

def one(x, tag):
    return next((c for c in x if isinstance(c, list) and c and c[0] == tag), None)
