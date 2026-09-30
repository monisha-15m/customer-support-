import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import SYSTEM_PROMPT

load_dotenv()

app = Flask(__name__)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_ITEMS = 20
PLACEHOLDER_KEY = "your_gemini_api_key_here"


def build_contents(history, message):
    contents = []

    if isinstance(history, list):
        for item in history[-MAX_HISTORY_ITEMS:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            text = str(item.get("text", "")).strip()
            if role in ("user", "model") and text:
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=text)])
                )

    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    return contents


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == PLACEHOLDER_KEY:
        return jsonify({"error": "The Gemini API key is missing. Add it to the .env file."}), 500

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"error": "Please type a message before sending."}), 400

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": f"Messages can be up to {MAX_MESSAGE_LENGTH} characters long."}), 400

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=build_contents(data.get("history"), message),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        reply = (response.text or "").strip()
    except Exception:
        return jsonify({"error": "The assistant is unavailable right now. Please try again in a moment."}), 502

    if not reply:
        return jsonify({"error": "I couldn't generate a reply. Please try rephrasing your question."}), 502

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
