"""Gemini Assistant - Alexa custom skill backend (AWS Lambda, Python, stdlib only).

No third-party dependencies: the handler parses the Alexa JSON request,
forwards the user's question to the Google Gemini API, cleans the answer
for voice (plain text, no markdown, no URLs), and returns an Alexa
response. The Gemini API key is NEVER in this file: it comes from the
Lambda environment variable GEMINI_API_KEY.
"""

import json
import os
import re
import urllib.error
import urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_HOST = "https://generativelanguage.googleapis.com"

SYSTEM_PROMPT = (
    "You are a voice assistant answering through Alexa. "
    "Answer briefly: at most 3 short sentences, plain text only, "
    "no markdown, no lists, no URLs, no special characters. "
    "Answer in the same language as the user's question."
)

TEXTS = {
    "en": {
        "welcome": "Hi! Ask me anything, and I will answer briefly.",
        "help": "Just ask me a question, for example: what is the capital of France?",
        "goodbye": "Goodbye!",
        "fallback": "I did not catch that. Please ask your question again.",
        "no_question": "What would you like to ask?",
        "not_configured": "This skill is not configured yet. The owner needs to add the Gemini API key.",
        "ai_error": "Sorry, I could not reach the AI service right now.",
        "no_answer": "Sorry, I did not get an answer. Please try another question.",
    },
    "ar": {
        "welcome": "اهلا! اسالني اي سؤال، وانا هجاوبك باختصار.",
        "help": "اسالني اي سؤال، مثلا: عاصمة فرنسا ايه؟",
        "goodbye": "مع السلامة!",
        "fallback": "مفهمتش السؤال. ممكن تعيد سؤالك تاني؟",
        "no_question": "عايز تسال عن ايه؟",
        "not_configured": "المهارة دي لسه مش متظبطة. صاحبها لازم يضيف مفتاح Gemini.",
        "ai_error": "عذرا، مقدرتش اوصل لخدمة الذكاء الاصطناعي دلوقتي.",
        "no_answer": "معلش، موصلنيش رد. جرب سؤال تاني.",
    },
}


def _lang(locale):
    return "ar" if (locale or "").lower().startswith("ar") else "en"


def _escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _clean(text):
    """Strip markdown/links/list markers so Alexa speaks plain text."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_#`>~]+", "", text)
    text = re.sub(r"(^|\s)-\s+", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _ask_gemini(question, api_key):
    url = "%s/v1beta/models/%s:generateContent" % (API_HOST, MODEL)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": question}]}],
        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("gemini_http_%s" % e.code)
    except Exception:
        raise RuntimeError("gemini_error")
    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        text = ""
    return text


def _response(text, end, reprompt=None):
    resp = {
        "outputSpeech": {
            "type": "SSML",
            "ssml": "<speak>%s</speak>" % _escape(text),
        },
        "shouldEndSession": end,
    }
    if reprompt:
        resp["reprompt"] = {
            "outputSpeech": {
                "type": "SSML",
                "ssml": "<speak>%s</speak>" % _escape(reprompt),
            }
        }
    return {"version": "1.0", "response": resp}


def lambda_handler(event, context):
    request = event.get("request", {})
    rtype = request.get("type")
    t = TEXTS[_lang(request.get("locale", "en-US"))]

    if rtype == "LaunchRequest":
        return _response(t["welcome"], end=False, reprompt=t["welcome"])

    if rtype == "IntentRequest":
        intent = request.get("intent", {})
        name = intent.get("name", "")

        if name == "AskGeminiIntent":
            slots = intent.get("slots", {}) or {}
            question = ((slots.get("question") or {}).get("value") or "").strip()
            if not question:
                return _response(t["no_question"], end=False, reprompt=t["no_question"])
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                return _response(t["not_configured"], end=True)
            try:
                answer = _clean(_ask_gemini(question, api_key))
            except RuntimeError:
                return _response(t["ai_error"], end=True)
            if not answer:
                return _response(t["no_answer"], end=True)
            return _response(answer, end=True)

        if name == "AMAZON.HelpIntent":
            return _response(t["help"], end=False, reprompt=t["help"])

        if name in ("AMAZON.CancelIntent", "AMAZON.StopIntent"):
            return _response(t["goodbye"], end=True)

        if name == "AMAZON.FallbackIntent":
            return _response(t["fallback"], end=False, reprompt=t["fallback"])

    if rtype == "SessionEndedRequest":
        return {"version": "1.0", "response": {}}

    return _response(t["fallback"], end=True)


# Alias so both entry-point names work.
handler = lambda_handler
