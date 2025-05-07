import random
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import logging
import difflib

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")

# Dictionary to store context for each chat
chat_context = {}

# Define the owner (your phone number or identifier) who can control chat pausing
OWNER_ID = '917439228809'

BLOCKED_KEYWORDS = ["crush", "tuition", "test", "school", "gay", "LGBTQ"]
ONE_TIME_TRIGGERS = ["who are you", "what's your name", "are you krishna", "who made you"]

# Load instructions from external file
with open("instructions.txt", "r", encoding="utf-8") as f:
    instructions = f.read().strip()

# Define a list of jokes to choose from
jokes = [
    "You really like asking that, huh?",
    "Is it Groundhog Day, or did we just talk about this?",
    "Is this a case of déjà vu, or am I just that predictable?",
    "I think you've asked this before, but let's try again!",
    "Are you trying to start a tradition with this question?"
]

# Utility: Check for repeated assistant response
def is_duplicate_response(new_text, context, threshold=0.92):
    for message in reversed(context):
        if message['role'] == 'assistant':
            similarity = difflib.SequenceMatcher(None, new_text.strip().lower(), message['content'].strip().lower()).ratio()
            if similarity >= threshold:
                return True
    return False

@app.route("/", methods=["GET"])
def home():
    return "Alien is alive 🚀", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if not request.is_json:
        logger.error("Request content type is not JSON")
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()

    if 'message' not in data:
        logger.error("Missing 'message' field in request")
        return jsonify({"error": "Missing 'message' field in request"}), 400

    user_message = data['message']
    sender_number = data.get('sender', '')
    logger.info(f"Received message: {user_message} from {sender_number}")

    if sender_number not in chat_context:
        chat_context[sender_number] = [{"role": "system", "content": instructions}] 

    normalized = user_message.lower().strip()

    # Check for blocked keywords
    if any(word in normalized for word in BLOCKED_KEYWORDS):
        chat_context[sender_number] = [m for m in chat_context[sender_number] if not any(word in m.get("content", "").lower() for word in BLOCKED_KEYWORDS)]
        logger.info(f"Blocked message. Updated context: {chat_context[sender_number]}")
    elif not any(trigger in normalized for trigger in ONE_TIME_TRIGGERS):
        chat_context[sender_number].append({"role": "user", "content": user_message})
    else:
        logger.info("Skipped appending one-time trigger to context.")

    # Limit to last 20 interactions (excluding system prompt)
    chat_context[sender_number] = chat_context[sender_number][:1] + chat_context[sender_number][-20:]

    # Build payload
    contents = []
    for message in chat_context[sender_number]:
        contents.append({"role": message['role'], "parts": [{"text": message['content']}]})

    payload = {"contents": contents}

    try:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }

        logger.info("Sending request to Gemini API")
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        gemini_response = response.json()
        try:
            generated_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Generated response: {generated_text[:100]}...")

            # Check if assistant is repeating itself
            if is_duplicate_response(generated_text, chat_context[sender_number]):
                # Randomly select a joke from the list
                generated_text += " " + random.choice(jokes)

            chat_context[sender_number].append({"role": "assistant", "content": generated_text})

            return jsonify({"success": True, "response": generated_text})

        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing Gemini API response: {e}")
            logger.error(f"Response structure: {gemini_response}")
            return jsonify({"error": "Failed to parse Gemini API response", "details": str(e)}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API: {e}")
        return jsonify({"error": "Failed to communicate with Gemini API", "details": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
