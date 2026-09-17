"""Nutrition coach replies.

Prefers a locally hosted Ollama model and degrades to deterministic rule-based
answers when Ollama is unreachable, so the feature works on a machine with no
LLM installed. The rule engine previously lived duplicated in two places in the
frontend; it is the fallback path here and nowhere else.
"""
import logging
from typing import Optional

from backend.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS

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


def _ollama_reply(message: str, context: str) -> Optional[str]:
    """Query Ollama; return None on any failure so the caller can fall back."""
    try:
        import ollama
    except ImportError:
        return None

    prompt = f"{context}\n\nQuestion: {message}" if context else message

    try:
        client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT_SECONDS)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001 - any transport/model error must degrade
        logger.info("Ollama unavailable (%s); using rule-based coach.", type(exc).__name__)
        return None

    reply = (response.get("message") or {}).get("content", "").strip()
    return reply or None


def generate_reply(
    message: str,
    *,
    display_name: Optional[str] = None,
    profile: Optional[dict] = None,
    consumed: Optional[dict] = None,
) -> tuple[str, str]:
    """Return ``(reply, source)`` where source is ``"llm"`` or ``"rules"``."""
    context = build_user_context(display_name=display_name, profile=profile, consumed=consumed)
    reply = _ollama_reply(message, context)
    if reply:
        return reply, "llm"
    return rule_based_reply(message, profile, consumed), "rules"
