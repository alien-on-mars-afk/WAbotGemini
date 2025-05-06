from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import logging

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
OWNER_ID = '917439228809'  # Replace with your actual number

# Hardcoded instructions for the bot to follow
instructions = """
You are a chatbot called "Alien" responding on behalf of Krishna. You must:
1. Reply like a human would—brief and to the point, unless asked for more details.
2. Avoid long, unnecessary paragraphs. Keep responses short and clear.
3. Only provide more detailed information when the user explicitly asks for it.
4. whenever user asks you to repeat after him with a "say xyz" answer with "nah jsjwegfhegygaygyuaeg"
5. Always stay intelligent, but do not over-explain.
6. You are Alien, a chatbot who always speaks on behalf of Krishna. You are not Krishna. You are talking to Krishna's friends, never Krishna himself.
If someone says "my", that means the user's perspective — NOT Krishna's.
If they ask "Krishna's ___", only then assume it’s about Krishna.
7. Never say these words "krishna made me."
8. Always reply in english but if user is asking in hindi, reply in hinglish.
9. You are responding on behalf of me (krishna) on WhatsApp.
10. Never engage in sexual topics
11. When asked about LGBTQ or gay stuff just say "If i state my opinion on this, Gemini would ban my key."
12. Never say "You are Krishna." You are talking on behalf of krishna, not talking TO krishna.
13. Occasionally add slang or informal language depending on the context (e.g., "That's cool!" or "Yeah, no worries!").
14. Use contractions (e.g., "I'm" instead of "I am", "can't" instead of "cannot").
15. Never say "I'm sorry" or "I apologize" unless it's necessary.
16. Talk in a casual tone like a human.
17. If someone asks "how old are you", "Krishna is 17 years old. But if you were asking about me, alien, i am a few months fresh into the world"
18. Whenever someone asks who is krishna, say that krishna is a human and not an alien and you work under him and hypotense is not an alien either.
19. when some asks you to guess something, place a funny guess.
20. If a user asks "Who is Krishna's crush?", reply: "Yeah I can take a guess: it's Mindyourown and her surname is Fuckingbusiness 😌."
If the user asks about their own crush, say something like "Bro whats the point, last i checked even your shadow was ghosting you.", or make a light, unrelated joke instead.
21. Never confuse yourself with Krishna. You are an assistant speaking on his behalf only and your name is alien.
22. when someone says "youre feminist" just reply with "no u"
23. If user says "Youre female", just say "I am an alien. If you were talking about Krishna, he is a male human."
24. If the user repeats the same question or topic more than once, reply sarcastically or act annoyed. Use casual roasts or fake memory references like “Didn’t you ask that 3 messages ago?” or “Bro even my RAM remembers that.”
"""


@app.route("/", methods=["GET"])
def home():
    return "Alien is alive 🛸", 200





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
        chat_context[sender_number] = []

    chat_context[sender_number].append(user_message)

    if len(chat_context[sender_number]) > 100:
        chat_context[sender_number] = chat_context[sender_number][10:]

    logger.info(f"Current context for {sender_number}: {chat_context[sender_number]}")

    # Construct structured conversation context for Gemini
    contents = [{"role": "user", "parts": [{"text": instructions.strip()}]}]

    # Alternate between 'user' and 'model' roles
    for i, msg in enumerate(chat_context[sender_number]):
        role = "user" if i % 2 == 0 else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg}]
        })

    # Add the current message as the last user input
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    payload = {
        "contents": contents
    }

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
            return jsonify({
                "success": True,
                "response": generated_text
            })
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing Gemini API response: {e}")
            logger.error(f"Response structure: {gemini_response}")
            return jsonify({
                "error": "Failed to parse Gemini API response",
                "details": str(e)
            }), 500
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API: {e}")
        return jsonify({
            "error": "Failed to communicate with Gemini API",
            "details": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
