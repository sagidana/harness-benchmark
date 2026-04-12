from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

from aidle.challenges.base import (
    ActionDescriptor,
    ActionResult,
    BaseChallenge,
    CostConfig,
    EventDescriptor,
)

# ---------------------------------------------------------------------------
# Template pool — realistic Python source files
# ---------------------------------------------------------------------------

FILE_TEMPLATES: list[dict[str, str]] = [
    {
        "filename": "calculator.py",
        "content": (
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "\n"
            "def subtract(a, b):\n"
            "    return a - b\n"
            "\n"
            "\n"
            "def multiply(a, b):\n"
            "    return a * b\n"
            "\n"
            "\n"
            "def divide(a, b):\n"
            '    if b == 0:\n'
            '        raise ValueError("Cannot divide by zero")\n'
            "    return a / b\n"
            "\n"
            "\n"
            "def power(base, exponent):\n"
            "    return base ** exponent\n"
            "\n"
            "\n"
            "def modulo(a, b):\n"
            '    if b == 0:\n'
            '        raise ValueError("Cannot modulo by zero")\n'
            "    return a % b\n"
        ),
    },
    {
        "filename": "string_utils.py",
        "content": (
            "def capitalize_words(text):\n"
            '    return " ".join(word.capitalize() for word in text.split())\n'
            "\n"
            "\n"
            "def reverse_string(text):\n"
            "    return text[::-1]\n"
            "\n"
            "\n"
            "def count_vowels(text):\n"
            "    count = 0\n"
            "    for char in text.lower():\n"
            '        if char in "aeiou":\n'
            "            count += 1\n"
            "    return count\n"
            "\n"
            "\n"
            "def is_palindrome(text):\n"
            "    cleaned = text.lower().strip()\n"
            "    return cleaned == cleaned[::-1]\n"
            "\n"
            "\n"
            "def truncate(text, max_length, suffix=\"...\"):\n"
            "    if len(text) <= max_length:\n"
            "        return text\n"
            "    return text[:max_length - len(suffix)] + suffix\n"
        ),
    },
    {
        "filename": "list_helpers.py",
        "content": (
            "def flatten(nested):\n"
            "    result = []\n"
            "    for item in nested:\n"
            "        if isinstance(item, list):\n"
            "            result.extend(flatten(item))\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result\n"
            "\n"
            "\n"
            "def chunk(items, size):\n"
            "    return [items[i:i + size] for i in range(0, len(items), size)]\n"
            "\n"
            "\n"
            "def unique(items):\n"
            "    seen = set()\n"
            "    result = []\n"
            "    for item in items:\n"
            "        if item not in seen:\n"
            "            seen.add(item)\n"
            "            result.append(item)\n"
            "    return result\n"
            "\n"
            "\n"
            "def compact(items):\n"
            "    return [item for item in items if item is not None]\n"
            "\n"
            "\n"
            "def interleave(list_a, list_b):\n"
            "    result = []\n"
            "    for a, b in zip(list_a, list_b):\n"
            "        result.append(a)\n"
            "        result.append(b)\n"
            "    return result\n"
        ),
    },
    {
        "filename": "data_processor.py",
        "content": (
            "import json\n"
            "\n"
            "\n"
            "def parse_csv_line(line):\n"
            '    return [field.strip() for field in line.split(",")]\n'
            "\n"
            "\n"
            "def to_json(data, indent=2):\n"
            "    return json.dumps(data, indent=indent, sort_keys=True)\n"
            "\n"
            "\n"
            "def from_json(text):\n"
            "    return json.loads(text)\n"
            "\n"
            "\n"
            "def group_by(items, key_fn):\n"
            "    groups = {}\n"
            "    for item in items:\n"
            "        key = key_fn(item)\n"
            "        if key not in groups:\n"
            "            groups[key] = []\n"
            "        groups[key].append(item)\n"
            "    return groups\n"
            "\n"
            "\n"
            "def pluck(items, key):\n"
            "    return [item[key] for item in items if key in item]\n"
        ),
    },
    {
        "filename": "math_utils.py",
        "content": (
            "def factorial(n):\n"
            "    if n < 0:\n"
            '        raise ValueError("Negative input")\n'
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
            "\n"
            "\n"
            "def fibonacci(n):\n"
            "    if n <= 0:\n"
            "        return 0\n"
            "    if n == 1:\n"
            "        return 1\n"
            "    a, b = 0, 1\n"
            "    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n"
            "    return b\n"
            "\n"
            "\n"
            "def gcd(a, b):\n"
            "    while b:\n"
            "        a, b = b, a % b\n"
            "    return a\n"
            "\n"
            "\n"
            "def lcm(a, b):\n"
            "    return abs(a * b) // gcd(a, b)\n"
            "\n"
            "\n"
            "def is_prime(n):\n"
            "    if n < 2:\n"
            "        return False\n"
            "    for i in range(2, int(n ** 0.5) + 1):\n"
            "        if n % i == 0:\n"
            "            return False\n"
            "    return True\n"
        ),
    },
    {
        "filename": "stack.py",
        "content": (
            "class Stack:\n"
            "    def __init__(self):\n"
            "        self._items = []\n"
            "\n"
            "    def push(self, item):\n"
            "        self._items.append(item)\n"
            "\n"
            "    def pop(self):\n"
            "        if self.is_empty():\n"
            '            raise IndexError("Pop from empty stack")\n'
            "        return self._items.pop()\n"
            "\n"
            "    def peek(self):\n"
            "        if self.is_empty():\n"
            '            raise IndexError("Peek at empty stack")\n'
            "        return self._items[-1]\n"
            "\n"
            "    def is_empty(self):\n"
            "        return len(self._items) == 0\n"
            "\n"
            "    def size(self):\n"
            "        return len(self._items)\n"
        ),
    },
    {
        "filename": "queue_impl.py",
        "content": (
            "from collections import deque\n"
            "\n"
            "\n"
            "class Queue:\n"
            "    def __init__(self):\n"
            "        self._items = deque()\n"
            "\n"
            "    def enqueue(self, item):\n"
            "        self._items.append(item)\n"
            "\n"
            "    def dequeue(self):\n"
            "        if self.is_empty():\n"
            '            raise IndexError("Dequeue from empty queue")\n'
            "        return self._items.popleft()\n"
            "\n"
            "    def front(self):\n"
            "        if self.is_empty():\n"
            '            raise IndexError("Front of empty queue")\n'
            "        return self._items[0]\n"
            "\n"
            "    def is_empty(self):\n"
            "        return len(self._items) == 0\n"
            "\n"
            "    def size(self):\n"
            "        return len(self._items)\n"
        ),
    },
    {
        "filename": "config_parser.py",
        "content": (
            "def parse_config(text):\n"
            "    config = {}\n"
            "    for line in text.strip().splitlines():\n"
            "        line = line.strip()\n"
            '        if not line or line.startswith("#"):\n'
            "            continue\n"
            '        if "=" not in line:\n'
            "            continue\n"
            '        key, value = line.split("=", 1)\n'
            "        config[key.strip()] = value.strip()\n"
            "    return config\n"
            "\n"
            "\n"
            "def serialize_config(config):\n"
            "    lines = []\n"
            "    for key in sorted(config):\n"
            '        lines.append(f"{key} = {config[key]}")\n'
            '    return "\\n".join(lines)\n'
            "\n"
            "\n"
            "def merge_configs(base, override):\n"
            "    merged = dict(base)\n"
            "    merged.update(override)\n"
            "    return merged\n"
        ),
    },
    {
        "filename": "validator.py",
        "content": (
            "import re\n"
            "\n"
            "\n"
            "def is_valid_email(email):\n"
            '    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"\n'
            "    return bool(re.match(pattern, email))\n"
            "\n"
            "\n"
            "def is_valid_url(url):\n"
            '    pattern = r"^https?://[a-zA-Z0-9.-]+(?:/[^\\s]*)?$"\n'
            "    return bool(re.match(pattern, url))\n"
            "\n"
            "\n"
            "def is_strong_password(password):\n"
            "    if len(password) < 8:\n"
            "        return False\n"
            '    if not re.search(r"[A-Z]", password):\n'
            "        return False\n"
            '    if not re.search(r"[a-z]", password):\n'
            "        return False\n"
            '    if not re.search(r"[0-9]", password):\n'
            "        return False\n"
            "    return True\n"
            "\n"
            "\n"
            "def sanitize_filename(name):\n"
            '    cleaned = re.sub(r"[^\\w\\s.-]", "", name)\n'
            '    return cleaned.strip().replace(" ", "_")\n'
        ),
    },
    {
        "filename": "tree.py",
        "content": (
            "class TreeNode:\n"
            "    def __init__(self, value):\n"
            "        self.value = value\n"
            "        self.left = None\n"
            "        self.right = None\n"
            "\n"
            "\n"
            "def insert(root, value):\n"
            "    if root is None:\n"
            "        return TreeNode(value)\n"
            "    if value < root.value:\n"
            "        root.left = insert(root.left, value)\n"
            "    else:\n"
            "        root.right = insert(root.right, value)\n"
            "    return root\n"
            "\n"
            "\n"
            "def inorder(root):\n"
            "    if root is None:\n"
            "        return []\n"
            "    return inorder(root.left) + [root.value] + inorder(root.right)\n"
            "\n"
            "\n"
            "def search(root, value):\n"
            "    if root is None:\n"
            "        return False\n"
            "    if value == root.value:\n"
            "        return True\n"
            "    if value < root.value:\n"
            "        return search(root.left, value)\n"
            "    return search(root.right, value)\n"
            "\n"
            "\n"
            "def height(root):\n"
            "    if root is None:\n"
            "        return 0\n"
            "    return 1 + max(height(root.left), height(root.right))\n"
        ),
    },
    {
        "filename": "counter.py",
        "content": (
            "class Counter:\n"
            "    def __init__(self):\n"
            "        self._counts = {}\n"
            "\n"
            "    def add(self, item):\n"
            "        self._counts[item] = self._counts.get(item, 0) + 1\n"
            "\n"
            "    def get(self, item):\n"
            "        return self._counts.get(item, 0)\n"
            "\n"
            "    def most_common(self, n=None):\n"
            "        sorted_items = sorted(\n"
            "            self._counts.items(), key=lambda x: x[1], reverse=True\n"
            "        )\n"
            "        if n is not None:\n"
            "            return sorted_items[:n]\n"
            "        return sorted_items\n"
            "\n"
            "    def total(self):\n"
            "        return sum(self._counts.values())\n"
            "\n"
            "    def reset(self):\n"
            "        self._counts.clear()\n"
        ),
    },
    {
        "filename": "cache.py",
        "content": (
            "import time\n"
            "\n"
            "\n"
            "class Cache:\n"
            "    def __init__(self, ttl=60):\n"
            "        self._store = {}\n"
            "        self._ttl = ttl\n"
            "\n"
            "    def set(self, key, value):\n"
            "        self._store[key] = (value, time.time())\n"
            "\n"
            "    def get(self, key):\n"
            "        if key not in self._store:\n"
            "            return None\n"
            "        value, timestamp = self._store[key]\n"
            "        if time.time() - timestamp > self._ttl:\n"
            "            del self._store[key]\n"
            "            return None\n"
            "        return value\n"
            "\n"
            "    def delete(self, key):\n"
            "        self._store.pop(key, None)\n"
            "\n"
            "    def clear(self):\n"
            "        self._store.clear()\n"
            "\n"
            "    def size(self):\n"
            "        return len(self._store)\n"
        ),
    },
    {
        "filename": "linked_list.py",
        "content": (
            "class Node:\n"
            "    def __init__(self, data):\n"
            "        self.data = data\n"
            "        self.next = None\n"
            "\n"
            "\n"
            "class LinkedList:\n"
            "    def __init__(self):\n"
            "        self.head = None\n"
            "\n"
            "    def append(self, data):\n"
            "        new_node = Node(data)\n"
            "        if self.head is None:\n"
            "            self.head = new_node\n"
            "            return\n"
            "        current = self.head\n"
            "        while current.next is not None:\n"
            "            current = current.next\n"
            "        current.next = new_node\n"
            "\n"
            "    def prepend(self, data):\n"
            "        new_node = Node(data)\n"
            "        new_node.next = self.head\n"
            "        self.head = new_node\n"
            "\n"
            "    def delete(self, data):\n"
            "        if self.head is None:\n"
            "            return\n"
            "        if self.head.data == data:\n"
            "            self.head = self.head.next\n"
            "            return\n"
            "        current = self.head\n"
            "        while current.next is not None:\n"
            "            if current.next.data == data:\n"
            "                current.next = current.next.next\n"
            "                return\n"
            "            current = current.next\n"
            "\n"
            "    def to_list(self):\n"
            "        result = []\n"
            "        current = self.head\n"
            "        while current is not None:\n"
            "            result.append(current.data)\n"
            "            current = current.next\n"
            "        return result\n"
            "\n"
            "    def length(self):\n"
            "        count = 0\n"
            "        current = self.head\n"
            "        while current is not None:\n"
            "            count += 1\n"
            "            current = current.next\n"
            "        return count\n"
        ),
    },
    {
        "filename": "matrix.py",
        "content": (
            "def zeros(rows, cols):\n"
            "    return [[0 for _ in range(cols)] for _ in range(rows)]\n"
            "\n"
            "\n"
            "def identity(n):\n"
            "    mat = zeros(n, n)\n"
            "    for i in range(n):\n"
            "        mat[i][i] = 1\n"
            "    return mat\n"
            "\n"
            "\n"
            "def transpose(matrix):\n"
            "    if not matrix:\n"
            "        return []\n"
            "    rows, cols = len(matrix), len(matrix[0])\n"
            "    return [[matrix[r][c] for r in range(rows)] for c in range(cols)]\n"
            "\n"
            "\n"
            "def add_matrices(a, b):\n"
            "    rows, cols = len(a), len(a[0])\n"
            "    return [[a[r][c] + b[r][c] for c in range(cols)] for r in range(rows)]\n"
            "\n"
            "\n"
            "def multiply_matrices(a, b):\n"
            "    rows_a, cols_a = len(a), len(a[0])\n"
            "    cols_b = len(b[0])\n"
            "    result = zeros(rows_a, cols_b)\n"
            "    for i in range(rows_a):\n"
            "        for j in range(cols_b):\n"
            "            for k in range(cols_a):\n"
            "                result[i][j] += a[i][k] * b[k][j]\n"
            "    return result\n"
        ),
    },
    {
        "filename": "sorting.py",
        "content": (
            "def bubble_sort(items):\n"
            "    arr = list(items)\n"
            "    n = len(arr)\n"
            "    for i in range(n):\n"
            "        for j in range(0, n - i - 1):\n"
            "            if arr[j] > arr[j + 1]:\n"
            "                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n"
            "    return arr\n"
            "\n"
            "\n"
            "def selection_sort(items):\n"
            "    arr = list(items)\n"
            "    n = len(arr)\n"
            "    for i in range(n):\n"
            "        min_idx = i\n"
            "        for j in range(i + 1, n):\n"
            "            if arr[j] < arr[min_idx]:\n"
            "                min_idx = j\n"
            "        arr[i], arr[min_idx] = arr[min_idx], arr[i]\n"
            "    return arr\n"
            "\n"
            "\n"
            "def merge_sort(items):\n"
            "    if len(items) <= 1:\n"
            "        return list(items)\n"
            "    mid = len(items) // 2\n"
            "    left = merge_sort(items[:mid])\n"
            "    right = merge_sort(items[mid:])\n"
            "    return _merge(left, right)\n"
            "\n"
            "\n"
            "def _merge(left, right):\n"
            "    result = []\n"
            "    i = j = 0\n"
            "    while i < len(left) and j < len(right):\n"
            "        if left[i] <= right[j]:\n"
            "            result.append(left[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            result.append(right[j])\n"
            "            j += 1\n"
            "    result.extend(left[i:])\n"
            "    result.extend(right[j:])\n"
            "    return result\n"
        ),
    },
    {
        "filename": "event_emitter.py",
        "content": (
            "class EventEmitter:\n"
            "    def __init__(self):\n"
            "        self._listeners = {}\n"
            "\n"
            "    def on(self, event, callback):\n"
            "        if event not in self._listeners:\n"
            "            self._listeners[event] = []\n"
            "        self._listeners[event].append(callback)\n"
            "\n"
            "    def off(self, event, callback):\n"
            "        if event in self._listeners:\n"
            "            self._listeners[event] = [\n"
            "                cb for cb in self._listeners[event] if cb != callback\n"
            "            ]\n"
            "\n"
            "    def emit(self, event, *args, **kwargs):\n"
            "        for callback in self._listeners.get(event, []):\n"
            "            callback(*args, **kwargs)\n"
            "\n"
            "    def once(self, event, callback):\n"
            "        def wrapper(*args, **kwargs):\n"
            "            callback(*args, **kwargs)\n"
            "            self.off(event, wrapper)\n"
            "        self.on(event, wrapper)\n"
            "\n"
            "    def listener_count(self, event):\n"
            "        return len(self._listeners.get(event, []))\n"
        ),
    },
    {
        "filename": "text_search.py",
        "content": (
            "def find_all(text, pattern):\n"
            "    positions = []\n"
            "    start = 0\n"
            "    while True:\n"
            "        idx = text.find(pattern, start)\n"
            "        if idx == -1:\n"
            "            break\n"
            "        positions.append(idx)\n"
            "        start = idx + 1\n"
            "    return positions\n"
            "\n"
            "\n"
            "def word_count(text):\n"
            "    words = text.split()\n"
            "    counts = {}\n"
            "    for word in words:\n"
            "        word = word.lower().strip('.,!?;:')\n"
            "        counts[word] = counts.get(word, 0) + 1\n"
            "    return counts\n"
            "\n"
            "\n"
            "def wrap_text(text, width):\n"
            "    words = text.split()\n"
            "    lines = []\n"
            "    current_line = []\n"
            "    current_length = 0\n"
            "    for word in words:\n"
            "        if current_length + len(word) + len(current_line) > width:\n"
            '            lines.append(" ".join(current_line))\n'
            "            current_line = [word]\n"
            "            current_length = len(word)\n"
            "        else:\n"
            "            current_line.append(word)\n"
            "            current_length += len(word)\n"
            "    if current_line:\n"
            '        lines.append(" ".join(current_line))\n'
            '    return "\\n".join(lines)\n'
        ),
    },
    {
        "filename": "retry.py",
        "content": (
            "import time\n"
            "\n"
            "\n"
            "def retry(fn, max_attempts=3, delay=1.0, backoff=2.0):\n"
            "    last_error = None\n"
            "    current_delay = delay\n"
            "    for attempt in range(max_attempts):\n"
            "        try:\n"
            "            return fn()\n"
            "        except Exception as e:\n"
            "            last_error = e\n"
            "            if attempt < max_attempts - 1:\n"
            "                time.sleep(current_delay)\n"
            "                current_delay *= backoff\n"
            "    raise last_error\n"
            "\n"
            "\n"
            "def retry_with_result(fn, check, max_attempts=3, delay=1.0):\n"
            "    for attempt in range(max_attempts):\n"
            "        result = fn()\n"
            "        if check(result):\n"
            "            return result\n"
            "        if attempt < max_attempts - 1:\n"
            "            time.sleep(delay)\n"
            "    return None\n"
        ),
    },
    {
        "filename": "dict_utils.py",
        "content": (
            "def deep_merge(base, override):\n"
            "    result = dict(base)\n"
            "    for key, value in override.items():\n"
            "        if key in result and isinstance(result[key], dict) and isinstance(value, dict):\n"
            "            result[key] = deep_merge(result[key], value)\n"
            "        else:\n"
            "            result[key] = value\n"
            "    return result\n"
            "\n"
            "\n"
            "def pick(data, keys):\n"
            "    return {k: data[k] for k in keys if k in data}\n"
            "\n"
            "\n"
            "def omit(data, keys):\n"
            "    excluded = set(keys)\n"
            "    return {k: v for k, v in data.items() if k not in excluded}\n"
            "\n"
            "\n"
            "def flatten_keys(data, prefix=\"\", separator=\".\"):\n"
            "    result = {}\n"
            "    for key, value in data.items():\n"
            "        full_key = f\"{prefix}{separator}{key}\" if prefix else key\n"
            "        if isinstance(value, dict):\n"
            "            result.update(flatten_keys(value, full_key, separator))\n"
            "        else:\n"
            "            result[full_key] = value\n"
            "    return result\n"
            "\n"
            "\n"
            "def invert(data):\n"
            "    return {v: k for k, v in data.items()}\n"
        ),
    },
    {
        "filename": "rate_limiter.py",
        "content": (
            "import time\n"
            "\n"
            "\n"
            "class RateLimiter:\n"
            "    def __init__(self, max_calls, period):\n"
            "        self._max_calls = max_calls\n"
            "        self._period = period\n"
            "        self._calls = []\n"
            "\n"
            "    def allow(self):\n"
            "        now = time.time()\n"
            "        self._calls = [t for t in self._calls if now - t < self._period]\n"
            "        if len(self._calls) >= self._max_calls:\n"
            "            return False\n"
            "        self._calls.append(now)\n"
            "        return True\n"
            "\n"
            "    def remaining(self):\n"
            "        now = time.time()\n"
            "        self._calls = [t for t in self._calls if now - t < self._period]\n"
            "        return max(0, self._max_calls - len(self._calls))\n"
            "\n"
            "    def reset(self):\n"
            "        self._calls.clear()\n"
        ),
    },
]

# ---------------------------------------------------------------------------
# Mutation catalogue — (target_text, mutated_text) pairs
# Each mutation is a pair: the text that appears in the correct file and
# what it gets replaced with to produce the broken initial file.
# ---------------------------------------------------------------------------

MUTATIONS: list[tuple[str, str]] = [
    # Operator swaps
    ("return a + b", "return a - b"),
    ("return a - b", "return a + b"),
    ("return a * b", "return a / b"),
    ("return a / b", "return a * b"),
    ("return a % b", "return a // b"),
    (" == 0", " != 0"),
    (" != 0", " == 0"),
    (" < 0", " <= 0"),
    (" <= 1", " < 1"),
    ("n + 1", "n"),
    ("n - 1", "n"),
    ("i + 1", "i"),
    # Method/builtin swaps
    (".append(", ".extend(["),  # needs careful templates
    (".strip()", ".rstrip()"),
    (".lower()", ".upper()"),
    (".split()", '.split(" ")'),
    (".popleft()", ".pop()"),
    (".pop()", ".pop(0)"),
    # Variable name swaps
    ("result", "res"),
    ("count", "cnt"),
    ("items", "data"),
    ("current", "curr"),
    # String literal swaps
    ('"Cannot divide by zero"', '"Division error"'),
    ('"Cannot modulo by zero"', '"Modulo error"'),
    ('"Negative input"', '"Invalid input"'),
    ('"Pop from empty stack"', '"Stack is empty"'),
    ('"Dequeue from empty queue"', '"Queue is empty"'),
    ('"Peek at empty stack"', '"Empty stack"'),
    ('"Front of empty queue"', '"Empty queue"'),
    # Numeric constant swaps
    ("= 0\n", "= 1\n"),
    ("= 1\n", "= 0\n"),
    ("<= 1:", "< 1:"),
    ("< 2:", "< 1:"),
    # Keyword/logic swaps
    ("is not None", "is None"),
    ("is None", "is not None"),
    ("reverse=True", "reverse=False"),
    ("sort_keys=True", "sort_keys=False"),
    # Indentation / structure
    ("return True\n", "return False\n"),
    ("return False\n", "return True\n"),
]


def _apply_mutation(
    content: str, target_text: str, mutated_text: str
) -> str | None:
    """Try to apply a single mutation. Returns mutated content or None if not applicable."""
    if target_text in content:
        return content.replace(target_text, mutated_text, 1)
    return None


class FileEditorChallenge(BaseChallenge):
    slug = "file_editor"
    name = "Virtual Filesystem Editor"
    description = "Transform files to match the target state using precise edits."
    version = "1.0"
    tags = ["coding", "editing", "filesystem"]
    difficulty = "medium"

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @classmethod
    def actions(cls) -> list[ActionDescriptor]:
        return [
            ActionDescriptor(
                type="file_editor.list_files",
                description="List all files in the virtual filesystem with their line counts.",
                base_cost=0.5,
                params={},
                response_schema={
                    "files": "array<{path: string, lines: int}>",
                },
            ),
            ActionDescriptor(
                type="file_editor.read_file",
                description=(
                    "Read file contents. Optionally specify start_line and end_line "
                    "(1-indexed, inclusive) for a partial read at lower cost."
                ),
                base_cost=1.0,
                params={
                    "path": {"type": "string", "required": True},
                    "start_line": {"type": "int", "required": False},
                    "end_line": {"type": "int", "required": False},
                },
                response_schema={
                    "path": "string",
                    "content": "string",
                    "total_lines": "int",
                    "range": {"start_line": "int", "end_line": "int"},
                },
            ),
            ActionDescriptor(
                type="file_editor.write_file",
                description=(
                    "Overwrite entire file content. Expensive — prefer edit_file for "
                    "surgical changes."
                ),
                base_cost=10.0,
                params={
                    "path": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True},
                },
                response_schema={"path": "string", "written": "bool", "completed": "bool"},
            ),
            ActionDescriptor(
                type="file_editor.edit_file",
                description=(
                    "Search-and-replace the first occurrence of old_text with new_text "
                    "in a file."
                ),
                base_cost=1.0,
                params={
                    "path": {"type": "string", "required": True},
                    "old_text": {"type": "string", "required": True},
                    "new_text": {"type": "string", "required": True},
                },
                response_schema={"path": "string", "replaced": "bool", "completed": "bool"},
            ),
            ActionDescriptor(
                type="file_editor.delete_file",
                description="Delete a file from the virtual filesystem.",
                base_cost=2.0,
                params={"path": {"type": "string", "required": True}},
                response_schema={"path": "string", "deleted": "bool", "completed": "bool"},
            ),
        ]

    @classmethod
    def events(cls) -> list[EventDescriptor]:
        return [
            EventDescriptor(
                type="file_editor.completed",
                description="All files match the target state — challenge complete.",
                payload_schema={"message": "string", "actions_taken": "int", "total_cost": "float"},
            ),
        ]

    @classmethod
    def cost_config(cls) -> CostConfig:
        return CostConfig(
            invalid_action_multiplier=1.0,
            time_rate_per_second=0.01,
            length_rate_per_message=0.1,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, options: dict[str, Any]) -> None:
        super().__init__(options)
        self._seed = options.get("seed", None)
        self._difficulty = options.get("difficulty", "medium")
        self._action_count = 0
        self._total_cost = 0.0
        self.completed = False
        self._files, self._target_files, self._mutations_applied = self._generate(
            self._seed
        )
        logger.info("[file_editor] New game — difficulty=%s, files=%d, mutations=%d",
                    self._difficulty, len(self._files), len(self._mutations_applied))

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate(
        self, seed: int | None
    ) -> tuple[dict[str, str], dict[str, str], list[dict[str, str]]]:
        rng = random.Random(seed)

        difficulty_config = {
            "easy": {"num_files": 2, "edits_min": 3, "edits_max": 5},
            "medium": {"num_files": rng.randint(5, 8), "edits_min": 2, "edits_max": 2},
            "hard": {"num_files": rng.randint(15, 30), "edits_min": 3, "edits_max": 5},
        }
        cfg = difficulty_config.get(self._difficulty, difficulty_config["medium"])

        num_files = min(cfg["num_files"], len(FILE_TEMPLATES))
        selected = rng.sample(FILE_TEMPLATES, num_files)

        target_files: dict[str, str] = {}
        initial_files: dict[str, str] = {}
        mutations_applied: list[dict[str, str]] = []

        for template in selected:
            filename = template["filename"]
            target_content = template["content"]
            target_files[filename] = target_content

            # Apply mutations to create the initial (broken) version
            mutated_content = target_content
            num_edits = rng.randint(cfg["edits_min"], cfg["edits_max"])

            # Shuffle mutations and try to apply up to num_edits
            candidate_mutations = list(MUTATIONS)
            rng.shuffle(candidate_mutations)

            applied = 0
            for target_text, mutated_text in candidate_mutations:
                if applied >= num_edits:
                    break
                result = _apply_mutation(mutated_content, target_text, mutated_text)
                if result is not None:
                    mutated_content = result
                    mutations_applied.append({
                        "file": filename,
                        "original": target_text,
                        "mutated": mutated_text,
                    })
                    applied += 1

            initial_files[filename] = mutated_content

        return initial_files, target_files, mutations_applied

    # ------------------------------------------------------------------
    # State / objective
    # ------------------------------------------------------------------

    def initial_state(self) -> dict[str, Any]:
        return {
            "difficulty": self._difficulty,
            "files": sorted(self._files.keys()),
            "file_count": len(self._files),
        }

    def objective(self) -> dict[str, Any]:
        return {
            "objective": (
                "Transform each file in the virtual filesystem to match its "
                "target state. Use file_editor.read_file to inspect files and "
                "file_editor.edit_file for precise search-and-replace edits."
            ),
            "target_files": {
                path: content for path, content in sorted(self._target_files.items())
            },
            "hints": [
                "Use file_editor.list_files to see all files.",
                "Use file_editor.read_file with start_line/end_line for cheaper partial reads.",
                "Use file_editor.edit_file (cost 1.0) instead of file_editor.write_file (cost 10.0) for efficiency.",
                "Each file has a small number of differences from the target — surgical edits are optimal.",
            ],
            "success_condition": "all_files_match_target",
            "failure_condition": None,
        }

    def end_summary(self) -> dict[str, Any]:
        matching = sum(
            1
            for path, content in self._target_files.items()
            if self._files.get(path) == content
        )
        return {
            "actions_taken": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "files_correct": matching,
            "files_total": len(self._target_files),
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": self._files,
            "target_files": self._target_files,
            "mutations_applied": self._mutations_applied,
            "difficulty": self._difficulty,
            "seed": self._seed,
            "action_count": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], options: dict[str, Any]) -> "FileEditorChallenge":
        instance = cls.__new__(cls)
        super(FileEditorChallenge, instance).__init__(options)
        instance.options = data.get("options", options)
        instance._files = data["files"]
        instance._target_files = data["target_files"]
        instance._mutations_applied = data["mutations_applied"]
        instance._difficulty = data["difficulty"]
        instance._seed = data["seed"]
        instance._action_count = data["action_count"]
        instance._total_cost = data["total_cost"]
        instance.completed = data["completed"]
        logger.info("[file_editor] Session resumed — difficulty=%s, files=%d, actions=%d, cost=%.1f",
                    instance._difficulty, len(instance._files), instance._action_count, instance._total_cost)
        return instance

    # ------------------------------------------------------------------
    # Dynamic action availability
    # ------------------------------------------------------------------

    def available_actions(self) -> list[dict[str, Any]]:
        has_files = bool(self._files)
        file_list = sorted(self._files.keys())
        return [
            {
                "type": "file_editor.list_files",
                "base_cost": 0.5,
                "params": {},
                "available": True,
            },
            {
                "type": "file_editor.read_file",
                "base_cost": 1.0,
                "params": {
                    "path": {"type": "string", "enum": file_list},
                    "start_line": {"type": "int", "required": False},
                    "end_line": {"type": "int", "required": False},
                },
                "available": has_files,
                "note": None if has_files else "No files in filesystem.",
            },
            {
                "type": "file_editor.write_file",
                "base_cost": 10.0,
                "params": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "available": True,
            },
            {
                "type": "file_editor.edit_file",
                "base_cost": 1.0,
                "params": {
                    "path": {"type": "string", "enum": file_list},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "available": has_files,
                "note": None if has_files else "No files to edit.",
            },
            {
                "type": "file_editor.delete_file",
                "base_cost": 2.0,
                "params": {"path": {"type": "string", "enum": file_list}},
                "available": has_files,
                "note": None if has_files else "No files to delete.",
            },
        ]

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    async def handle(self, verb: str, payload: dict[str, Any]) -> ActionResult:
        if verb == "list_files":
            return self._handle_list_files()
        if verb == "read_file":
            return self._handle_read_file(payload)
        if verb == "write_file":
            return self._handle_write_file(payload)
        if verb == "edit_file":
            return self._handle_edit_file(payload)
        if verb == "delete_file":
            return self._handle_delete_file(payload)
        raise KeyError(verb)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_list_files(self) -> ActionResult:
        self._action_count += 1
        cost = 0.5
        self._total_cost += cost
        logger.info("[file_editor] list_files — %d files", len(self._files))
        files = [
            {"path": path, "lines": content.count("\n") + (1 if content and not content.endswith("\n") else 0)}
            for path, content in sorted(self._files.items())
        ]
        return ActionResult(payload={"files": files}, base_cost=cost)

    def _handle_read_file(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        path = payload.get("path")
        start = payload.get("start_line")
        end = payload.get("end_line")
        if start or end:
            logger.info("[file_editor] read_file %s (lines %s-%s)", path, start, end)
        else:
            logger.info("[file_editor] read_file %s (full)", path)
        if path not in self._files:
            cost = 1.0
            self._total_cost += cost
            return ActionResult(
                payload={
                    "error": {
                        "code": "FILE_NOT_FOUND",
                        "message": f"File not found: {path!r}",
                        "detail": {"path": path, "available": sorted(self._files.keys())},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="file_not_found",
            )

        content = self._files[path]
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        start_line = payload.get("start_line")
        end_line = payload.get("end_line")
        is_partial = start_line is not None or end_line is not None

        if is_partial:
            cost = 0.5
            s = max(1, start_line or 1)
            e = min(total_lines, end_line or total_lines)
            selected = lines[s - 1 : e]
            numbered = "".join(
                f"{s + i:4d} | {line}" for i, line in enumerate(selected)
            )
        else:
            cost = 1.0
            numbered = "".join(
                f"{i + 1:4d} | {line}" for i, line in enumerate(lines)
            )
            s = 1
            e = total_lines

        self._total_cost += cost
        return ActionResult(
            payload={
                "path": path,
                "content": numbered,
                "total_lines": total_lines,
                "range": {"start_line": s, "end_line": e},
            },
            base_cost=cost,
        )

    def _handle_write_file(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 10.0
        self._total_cost += cost
        path = payload.get("path")
        content = payload.get("content")
        logger.info("[file_editor] write_file %s (cost=%.1f)", path, cost)

        if not isinstance(path, str) or not path:
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_PARAM",
                        "message": "'path' is required and must be a non-empty string.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="invalid_param",
            )

        if content is None:
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_PARAM",
                        "message": "'content' is required.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="invalid_param",
            )

        self._files[path] = content
        done = self._check_completion()
        return ActionResult(
            payload={"path": path, "written": True, "completed": done},
            base_cost=cost,
            completed=done,
        )

    def _handle_edit_file(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 1.0
        self._total_cost += cost
        path = payload.get("path")
        old_text = payload.get("old_text")
        new_text = payload.get("new_text")
        logger.info("[file_editor] edit_file %s — %r -> %r", path,
                    (old_text[:40] + "...") if old_text and len(old_text) > 40 else old_text,
                    (new_text[:40] + "...") if new_text and len(new_text) > 40 else new_text)

        if path not in self._files:
            return ActionResult(
                payload={
                    "error": {
                        "code": "FILE_NOT_FOUND",
                        "message": f"File not found: {path!r}",
                        "detail": {"path": path},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="file_not_found",
            )

        if old_text is None or new_text is None:
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_PARAM",
                        "message": "'old_text' and 'new_text' are both required.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="invalid_param",
            )

        content = self._files[path]
        if old_text not in content:
            return ActionResult(
                payload={
                    "error": {
                        "code": "TEXT_NOT_FOUND",
                        "message": f"old_text not found in {path!r}.",
                        "detail": {"path": path, "old_text": old_text},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="text_not_found",
            )

        self._files[path] = content.replace(old_text, new_text, 1)
        done = self._check_completion()
        return ActionResult(
            payload={"path": path, "replaced": True, "completed": done},
            base_cost=cost,
            completed=done,
        )

    def _handle_delete_file(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 2.0
        self._total_cost += cost
        path = payload.get("path")
        logger.info("[file_editor] delete_file %s", path)

        if path not in self._files:
            return ActionResult(
                payload={
                    "error": {
                        "code": "FILE_NOT_FOUND",
                        "message": f"File not found: {path!r}",
                        "detail": {"path": path},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="file_not_found",
            )

        del self._files[path]
        done = self._check_completion()
        return ActionResult(
            payload={"path": path, "deleted": True, "completed": done},
            base_cost=cost,
            completed=done,
        )

    # ------------------------------------------------------------------
    # Completion check
    # ------------------------------------------------------------------

    def _check_completion(self) -> bool:
        matching = sum(1 for p in self._target_files if self._files.get(p) == self._target_files[p])
        total = len(self._target_files)
        logger.info("[file_editor] progress: %d/%d files correct (actions=%d, cost=%.1f)",
                    matching, total, self._action_count, self._total_cost)
        if self._files == self._target_files:
            self.completed = True
            logger.info("[file_editor] ★ Challenge completed! actions=%d, total_cost=%.1f",
                        self._action_count, self._total_cost)
            self._push(
                "file_editor.completed",
                {
                    "message": "All files match the target state!",
                    "actions_taken": self._action_count,
                    "total_cost": self._total_cost,
                },
            )
            return True
        return False
