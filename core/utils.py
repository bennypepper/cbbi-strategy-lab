"""
core/utils.py
==============
Utility functions for the CBBI Strategy Lab.
"""

def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format a percentage value smartly based on its magnitude.
    Expects input that represents the raw percentage (e.g. 1500 for 1500%).
    
    Rules:
    - Under 1K: +150.5% (uses param decimal_places)
    - 1K to 1M: +1,500% (comma separated, no decimals)
    - Over 1M:  +1.50M% (M, B, T abbreviations)
    """
    sign = "+" if value > 0 else ""
    abs_v = abs(value)
    
    if abs_v >= 1e12:
        return f"{sign}{value/1e12:.2f}T%"
    elif abs_v >= 1e9:
        return f"{sign}{value/1e9:.2f}B%"
    elif abs_v >= 1e6:
        return f"{sign}{value/1e6:.2f}M%"
    elif abs_v >= 1e3:
        return f"{sign}{value:,.0f}%"
    else:
        return f"{sign}{value:,.{decimal_places}f}%"


def format_currency(value: float) -> str:
    """
    Format a USD currency value smartly based on its magnitude.
    
    Rules:
    - Under $1K: $150.55 (2 decimals)
    - $1K to $1M: $15,000 (comma separated, 0 decimals - cents don't matter)
    - Over $1M: $1.50M (M, B, T abbreviations)
    """
    sign = "-" if value < 0 else ""
    abs_v = abs(value)
    
    if abs_v >= 1e12:
        return f"{sign}${abs_v/1e12:.2f}T"
    elif abs_v >= 1e9:
        return f"{sign}${abs_v/1e9:.2f}B"
    elif abs_v >= 1e6:
        return f"{sign}${abs_v/1e6:.2f}M"
    elif abs_v >= 1e3:
        return f"{sign}${abs_v:,.0f}"
    else:
        return f"{sign}${abs_v:,.2f}"

