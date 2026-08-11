"""
Sparkline generator for asset price trends using Unicode block elements.
"""

from __future__ import annotations

BLOCKS = (" ", "▂", "▃", "▄", "▅", "▆", "▇", "█")


def generate_sparkline(values: list[float] | float, length: int = 5) -> str:
    """
    Generate a sparkline string from a list of float values or a single percentage change.

    Examples:
        generate_sparkline([10, 12, 11, 15, 14, 18, 20]) -> "[ ▂▃▅▇█]"
        generate_sparkline(8.5)  -> "[ ▃▅▇█]"
        generate_sparkline(-5.2) -> "[█▇▅▃ ]"
    """
    if isinstance(values, (int, float)):
        pct = float(values)
        if abs(pct) < 0.01:
            return "[▄▄▄▄▄]"
        if pct > 0:
            points = [10.0, 10.0 + pct * 0.25, 10.0 + pct * 0.5, 10.0 + pct * 0.75, 10.0 + pct]
        else:
            points = [10.0, 10.0 + pct * 0.25, 10.0 + pct * 0.5, 10.0 + pct * 0.75, 10.0 + pct]
        values = points

    if not values or len(values) < 2:
        return "[▄▄▄▄▄]"

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val

    bars = []
    for v in values:
        if val_range == 0:
            idx = 3
        else:
            normalized = (v - min_val) / val_range
            idx = int(normalized * (len(BLOCKS) - 1))
            idx = max(0, min(len(BLOCKS) - 1, idx))
        bars.append(BLOCKS[idx])

    return f"[{''.join(bars)}]"
