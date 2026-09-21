"""Nutrition coach replies.

Answers come from Gemini, called through a failover chain of
`(model, API key)` candidates, and degrade to deterministic rule-based answers
when every candidate is exhausted or no key is configured. The feature
therefore works on a machine with no credentials at all.

The rule engine previously lived duplicated in two places in the frontend; it
is the final fallback tier here and nowhere else.
"""
import logging
from functools import lru_cache
from typing import Optional

from backend.config import GEMINI_API_KEYS, GEMINI_MODELS, GEMINI_TIMEOUT_SECONDS
from backend.llm import LLMChain

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a nutrition coach inside a diet-tracking app. Give brief, practical, "
    "evidence-based guidance in at most four sentences. Use the user's own numbers "
    "when they are provided. You are an educational tool, not a clinician: if asked "
    "about a medical condition, medication, or a diagnosis, say so and recommend a "
    "registered dietitian or doctor."
)

DISCLAIMER_TRIGGERS = (
    "diabetes", "diabetic", "insulin", "medication", "medicine", "disease",
    "cancer", "pregnan", "thyroid", "kidney", "blood pressure", "cholesterol medication",
    "eating disorder", "anorexi", "bulimi",
)


def build_user_context(
    *,
    display_name: Optional[str],
    profile: Optional[dict],
    consumed: Optional[dict],
) -> str:
    """Render the caller's profile and today's intake as prompt context."""
    lines = []
    if display_name:
        lines.append(f"User: {display_name}")
    if profile:
        lines.append(
            "Profile: goal={goal}, diet={diet}, BMI={bmi}, BMR={bmr} kcal.".format(
                goal=profile.get("fitness_goal", "unknown"),
                diet=profile.get("dietary_preference", "None"),
                bmi=profile.get("bmi", "?"),
                bmr=profile.get("bmr", "?"),
            )
        )
        lines.append(
            "Daily targets: {cal} kcal, {p}g protein, {c}g carbs, {f}g fat.".format(
                cal=profile.get("target_calories", "?"),
                p=profile.get("target_protein", "?"),
                c=profile.get("target_carbs", "?"),
                f=profile.get("target_fat", "?"),
            )
        )
    if consumed:
        lines.append(
            "Consumed today: {cal} kcal, {p}g protein, {c}g carbs, {f}g fat.".format(
                cal=round(consumed.get("calories", 0)),
                p=round(consumed.get("protein", 0)),
                c=round(consumed.get("carbs", 0)),
                f=round(consumed.get("fat", 0)),
            )
        )
    return "\n".join(lines)


def _protein_sources(dietary_preference: Optional[str]) -> str:
    """Suggest protein sources the user will actually eat."""
    preference = (dietary_preference or "None").strip().lower()
    if preference == "vegan":
        return "Lentils, chickpeas, tofu, tempeh, soy milk, peanut butter and seitan all count."
    if preference == "vegetarian":
        return "Lentils, chickpeas, paneer, yoghurt, tofu and milk are all efficient sources."
    return "Lentils, paneer, tofu, eggs, fish and chicken are all efficient ways to reach it."


def rule_based_reply(message: str, profile: Optional[dict], consumed: Optional[dict]) -> str:
    """Deterministic fallback answers keyed on a few common intents."""
    lower = message.lower()

    if any(trigger in lower for trigger in DISCLAIMER_TRIGGERS):
        return (
            "That touches on a medical question, and this app is an educational tool "
            "rather than a clinical one. Please talk to a registered dietitian or your "
            "doctor for advice specific to your condition."
        )

    if "water" in lower or "hydrat" in lower:
        return (
            "Hydration matters. Around 2.5-3 litres of water a day is a reasonable "
            "starting point, and more if you are training hard or it is hot."
        )

    if "protein" in lower:
        if profile:
            return (
                f"Your daily protein target is {profile.get('target_protein', '?')}g, based on your "
                f"goal to {str(profile.get('fitness_goal', '')).lower()}. "
                f"{_protein_sources(profile.get('dietary_preference'))}"
            )
        return (
            "Protein supports muscle repair and satiety. Fill in your health profile "
            "and I can give you a specific daily target."
        )

    if "bmr" in lower or "bmi" in lower:
        if profile:
            return (
                f"Your BMR is {profile.get('bmr', '?')} kcal -- the energy you burn at complete rest -- "
                f"and your BMI is {profile.get('bmi', '?')}. Your calorie target adds your activity "
                "level on top of the BMR."
            )
        return "Add your age, height, weight and activity level and I can calculate your BMI and BMR."

    if "calorie" in lower or "eat" in lower or "remaining" in lower:
        if profile and consumed:
            target = float(profile.get("target_calories", 0) or 0)
            eaten = float(consumed.get("calories", 0) or 0)
            remaining = max(0.0, target - eaten)
            return (
                f"You have eaten {round(eaten)} kcal of your {round(target)} kcal target today, "
                f"leaving about {round(remaining)} kcal. Spending that on protein and fibre will "
                "keep you fuller than the same calories from refined carbohydrates."
            )
        return "Log a few meals and I can tell you how many calories you have left today."

    if "fiber" in lower or "fibre" in lower:
        return (
            "Aim for roughly 25-30g of fibre daily. Beans, lentils, oats, whole fruit and "
            "vegetables with the skin on are the easiest ways to get there."
        )

    if "lose weight" in lower or "weight loss" in lower or "fat loss" in lower:
        return (
            "A deficit of roughly 500 kcal a day tends to yield about 0.5 kg a week. Keep protein "
            "high and strength-train so most of the loss is fat rather than muscle."
        )

    return (
        "I can help with calories, macronutrients, fibre, hydration and meal ideas. Ask me "
        "something like 'how much protein do I need?' or 'how many calories do I have left?'"
    )


@lru_cache(maxsize=1)
def _chain() -> LLMChain:
    """The process-wide failover chain, built once from configuration."""
    return LLMChain(
        api_keys=GEMINI_API_KEYS,
        models=GEMINI_MODELS,
        timeout=GEMINI_TIMEOUT_SECONDS,
    )


def reset_chain() -> None:
    """Drop the cached chain. Used by tests after changing configuration."""
    _chain.cache_clear()


def _llm_reply(message: str, context: str) -> Optional[str]:
    """Ask Gemini; return None on any failure so the caller falls back."""
    chain = _chain()
    if not chain.configured:
        return None

    prompt = f"{context}\n\nQuestion: {message}" if context else message
    result = chain.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)

    if result.succeeded and result.reply is not None:
        return result.reply.text

    logger.info(
        "Coach falling back to rules after %s attempt(s): %s",
        result.attempts,
        ", ".join(f"{who}={kind.value}" for who, kind in result.failures) or "not configured",
    )
    return None


def generate_reply(
    message: str,
    *,
    display_name: Optional[str] = None,
    profile: Optional[dict] = None,
    consumed: Optional[dict] = None,
) -> tuple[str, str]:
    """Return ``(reply, source)`` where source is ``"llm"`` or ``"rules"``."""
    context = build_user_context(display_name=display_name, profile=profile, consumed=consumed)
    reply = _llm_reply(message, context)
    if reply:
        return reply, "llm"
    return rule_based_reply(message, profile, consumed), "rules"
