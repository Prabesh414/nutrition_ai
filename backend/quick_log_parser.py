"""Natural language meal logging parser.

Converts free-text meal descriptions (e.g. "2 boiled eggs and a bowl of oatmeal")
into structured meal items with calories and macronutrients. Uses Gemini REST
failover chain when configured, with deterministic keyword-matching fallback against
the food catalogue when offline or unconfigured.
"""
import json
import logging
import re
from typing import Optional
from sqlalchemy.orm import Session

from backend.chat import _chain
from backend.database import FoodItem
from backend.schemas import MealType, QuickLogAIResponse, QuickLogItemResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a nutrition logging assistant. Convert the user's natural language meal "
    "description into a JSON array of food items. Each item must contain:\n"
    '- "name": string (clean food name)\n'
    '- "quantity": float (portion count, e.g. 1.0, 2.0)\n'
    '- "meal_type": "Breakfast" | "Lunch" | "Dinner" | "Snack"\n'
    '- "calories": float (total energy in kcal for this quantity)\n'
    '- "protein": float (total protein in grams)\n'
    '- "carbs": float (total carbohydrates in grams)\n'
    '- "fat": float (total fat in grams)\n'
    '- "fiber": float (total dietary fiber in grams)\n'
    "Respond ONLY with a valid JSON array of objects. Do not wrap in markdown or backticks."
)


def _heuristic_parse(db: Session, text: str, default_meal_type: MealType = "Breakfast") -> list[QuickLogItemResponse]:
    """Deterministic fallback matching against the food catalogue."""
    # Split on commas, semicolons, ' and ', newlines
    raw_parts = re.split(r",|;|\band\b|\n", text, flags=re.IGNORECASE)
    items: list[QuickLogItemResponse] = []

    for part in raw_parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue

        # Extract leading quantity (e.g. "2 ", "1.5 ", "3x ")
        qty = 1.0
        qty_match = re.match(r"^(\d+(?:\.\d+)?)\s*(?:x\s*|cups?\s*|bowls?\s*|slices?\s*|pieces?\s*|g\s*|plates?\s*)?", part, re.IGNORECASE)
        query_text = part
        if qty_match:
            try:
                qty = float(qty_match.group(1))
                query_text = part[qty_match.end():].strip()
            except ValueError:
                qty = 1.0

        if not query_text:
            query_text = part

        # Search catalogue for best keyword match
        clean_name = re.sub(r"[^\w\s]", "", query_text).strip()
        matched = None
        if clean_name:
            matched = (
                db.query(FoodItem)
                .filter(FoodItem.name.ilike(f"%{clean_name}%"))
                .first()
            )
            if not matched:
                # Try first word
                first_word = clean_name.split()[0]
                if len(first_word) > 2:
                    matched = (
                        db.query(FoodItem)
                        .filter(FoodItem.name.ilike(f"%{first_word}%"))
                        .first()
                    )

        if matched:
            items.append(
                QuickLogItemResponse(
                    name=matched.name.title(),
                    quantity=round(qty, 1),
                    meal_type=default_meal_type,
                    calories=round(matched.calories * qty, 1),
                    protein=round(matched.protein * qty, 1),
                    carbs=round(matched.carbohydrates * qty, 1),
                    fat=round(matched.fat * qty, 1),
                    fiber=round(matched.fiber * qty, 1),
                    confidence=0.9,
                )
            )
        else:
            # Reasonable generic default for unrecognized items
            items.append(
                QuickLogItemResponse(
                    name=clean_name.title() or part.title(),
                    quantity=round(qty, 1),
                    meal_type=default_meal_type,
                    calories=round(150.0 * qty, 1),
                    protein=round(5.0 * qty, 1),
                    carbs=round(20.0 * qty, 1),
                    fat=round(5.0 * qty, 1),
                    fiber=round(2.0 * qty, 1),
                    confidence=0.5,
                )
            )

    return items


def parse_quick_log(
    db: Session,
    text: str,
    default_meal_type: Optional[MealType] = None,
) -> QuickLogAIResponse:
    """Parse text into meal items via LLM or fallback heuristics."""
    meal_slot: MealType = default_meal_type or "Breakfast"
    chain = _chain()

    if chain.configured:
        prompt = f"Extract foods from: '{text}'. Default meal slot: '{meal_slot}'."
        result = chain.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        if result.succeeded and result.reply and result.reply.text:
            raw_text = result.reply.text.strip()
            # Clean possible markdown block markers
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
            try:
                data = json.loads(raw_text)
                if isinstance(data, list) and len(data) > 0:
                    valid_slots = {"Breakfast", "Lunch", "Dinner", "Snack"}
                    items = []
                    for row in data:
                        slot = str(row.get("meal_type", meal_slot)).capitalize()
                        if slot not in valid_slots:
                            slot = meal_slot
                        items.append(
                            QuickLogItemResponse(
                                name=str(row.get("name", "Food Item")).title(),
                                quantity=float(row.get("quantity", 1.0)),
                                meal_type=slot,  # type: ignore[arg-type]
                                calories=max(0.0, float(row.get("calories", 0.0))),
                                protein=max(0.0, float(row.get("protein", 0.0))),
                                carbs=max(0.0, float(row.get("carbs", 0.0))),
                                fat=max(0.0, float(row.get("fat", 0.0))),
                                fiber=max(0.0, float(row.get("fiber", 0.0))),
                                confidence=1.0,
                            )
                        )
                    return QuickLogAIResponse(
                        parsed_items=items,
                        summary_note="Parsed with AI Nutrition Assistant",
                        source="llm",
                    )
            except (json.JSONDecodeError, ValueError, KeyError) as err:
                logger.info("LLM quick log JSON parse failed (%s), falling back to heuristics", err)

    heuristic_items = _heuristic_parse(db, text, default_meal_type=meal_slot)
    return QuickLogAIResponse(
        parsed_items=heuristic_items,
        summary_note="Extracted from food database catalog",
        source="heuristic",
    )
