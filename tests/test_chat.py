"""Nutrition coach replies and its Ollama fallback behaviour."""
import pytest

from backend.chat import generate_reply, rule_based_reply

API = "/api/v1"

VEGAN_PROFILE = {"fitness_goal": "Lose Weight", "dietary_preference": "Vegan",
                 "bmi": 21.3, "bmr": 1310, "target_calories": 1500,
                 "target_protein": 110, "target_carbs": 150, "target_fat": 50}
CONSUMED = {"calories": 600, "protein": 25, "carbs": 80, "fat": 15, "fiber": 7}


def test_protein_advice_respects_a_vegan_diet():
    """The coach used to recommend eggs, fish and chicken to vegans."""
    reply = rule_based_reply("how much protein do I need?", VEGAN_PROFILE, CONSUMED)
    lowered = reply.lower()
    assert "110" in reply
    for animal in ("egg", "fish", "chicken", "paneer"):
        assert animal not in lowered, reply


def test_protein_advice_for_vegetarians_allows_dairy_but_not_meat():
    profile = {**VEGAN_PROFILE, "dietary_preference": "Vegetarian"}
    lowered = rule_based_reply("protein sources?", profile, CONSUMED).lower()
    assert "paneer" in lowered
    assert "chicken" not in lowered and "fish" not in lowered


def test_calorie_question_uses_the_users_own_numbers():
    reply = rule_based_reply("how many calories do I have left?", VEGAN_PROFILE, CONSUMED)
    assert "600" in reply and "1500" in reply and "900" in reply


def test_medical_questions_are_deflected_to_a_professional():
    for question in ("what should I eat for my diabetes?",
                     "can I take this with my medication?",
                     "I think I have an eating disorder"):
        reply = rule_based_reply(question, VEGAN_PROFILE, CONSUMED).lower()
        assert "dietitian" in reply or "doctor" in reply, question


def test_unknown_question_gets_a_useful_prompt():
    assert "ask me" in rule_based_reply("what is the capital of Nepal?", None, None).lower()


def test_generate_reply_falls_back_to_rules_without_ollama(monkeypatch):
    monkeypatch.setattr("backend.chat._ollama_reply", lambda message, context: None)
    reply, source = generate_reply("protein?", profile=VEGAN_PROFILE, consumed=CONSUMED)
    assert source == "rules" and reply


def test_generate_reply_prefers_the_llm_when_available(monkeypatch):
    monkeypatch.setattr("backend.chat._ollama_reply", lambda message, context: "LLM answer")
    reply, source = generate_reply("protein?", profile=VEGAN_PROFILE, consumed=CONSUMED)
    assert (reply, source) == ("LLM answer", "llm")


def test_ollama_failure_is_swallowed(monkeypatch):
    """A broken Ollama must degrade, never 500."""
    def explode(*args, **kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr("ollama.Client", explode)
    _, source = generate_reply("protein?", profile=VEGAN_PROFILE, consumed=CONSUMED)
    assert source == "rules"


def test_chat_endpoint_requires_authentication(client):
    assert client.post(f"{API}/chat", json={"message": "hello"}).status_code == 401


def test_chat_endpoint_answers_with_the_callers_context(client, register_user, monkeypatch):
    monkeypatch.setattr("backend.chat._ollama_reply", lambda message, context: None)
    headers, _ = register_user("chat@example.com")
    client.put(f"{API}/profile", headers=headers, json={
        "age": 28, "gender": "Female", "height": 165, "weight": 58,
        "activity_level": "Lightly Active", "fitness_goal": "Lose Weight",
        "dietary_preference": "Vegan"})
    client.post(f"{API}/meals", headers=headers, json={"name": "Oats", "calories": 350})

    body = client.post(f"{API}/chat", headers=headers,
                       json={"message": "how many calories do I have left?"}).json()
    assert body["source"] == "rules"
    assert "350" in body["reply"]


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_chat_rejects_empty_or_oversized_messages(client, register_user, message):
    headers, _ = register_user()
    assert client.post(f"{API}/chat", headers=headers,
                       json={"message": message}).status_code == 422
