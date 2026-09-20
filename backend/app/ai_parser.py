import json
import re
from typing import Optional
from .config import settings
from .schemas import ParsedOrder, ParsedItem

ALIASES = {
    "atta": "Aashirvaad Atta",
    "aashirvaad": "Aashirvaad Atta",
    "flour": "Aashirvaad Atta",
    "oil": "Fortune Oil",
    "fortune": "Fortune Oil",
    "maggi": "Maggi",
    "salt": "Tata Salt",
    "milk": "Amul Milk",
    "parle": "Parle-G Biscuits",
    "parleg": "Parle-G Biscuits",
    "biscuits": "Parle-G Biscuits",
    "toothpaste": "Colgate Toothpaste",
    "colgate": "Colgate Toothpaste",
    "surf": "Surf Excel",
    "coke": "Coca Cola",
    "coca cola": "Coca Cola",
    "bread": "Britannia Bread",
}

PRODUCT_NAMES = [
    "Aashirvaad Atta", "Fortune Oil", "Maggi", "Tata Salt", "Amul Milk",
    "Parle-G Biscuits", "Colgate Toothpaste", "Surf Excel", "Coca Cola", "Britannia Bread"
]

def _fallback(text: str) -> ParsedOrder:
    lower = text.lower()
    items = []
    for alias, canonical in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
        if alias not in lower:
            continue
        patterns = [
            rf"(\d+)\s*(?:x\s*)?(?:{re.escape(alias)})",
            rf"(?:{re.escape(alias)})\s*(?:x\s*)?(\d+)",
        ]
        qty = None
        for pattern in patterns:
            m = re.search(pattern, lower)
            if m:
                qty = int(m.group(1))
                break
        if qty is None:
            qty = 1
        if not any(i.product == canonical for i in items):
            items.append(ParsedItem(product=canonical, quantity=qty))
    if not items:
        for p in PRODUCT_NAMES:
            if p.lower() in lower and not any(i.product == p for i in items):
                items.append(ParsedItem(product=p, quantity=1))
    return ParsedOrder(items=items, notes="Parsed locally" if items else "No supported product detected")

def parse_order(text: str) -> ParsedOrder:
    if not settings.gemini_api_key:
        return _fallback(text)
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = f'''You are an order parser for a small Indian kirana store. Return ONLY valid JSON matching this schema: {{"items":[{{"product":"canonical catalog name","quantity":1}}],"notes":""}}.\nCatalog: {PRODUCT_NAMES}\nRules: quantity must be a positive integer. Map common aliases such as atta->Aashirvaad Atta, oil->Fortune Oil, biscuits->Parle-G Biscuits, milk->Amul Milk. Do not invent products. Customer message: {text}'''
        response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return ParsedOrder.model_validate(data)
    except Exception:
        return _fallback(text)
