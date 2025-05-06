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
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent")

OWNER_ID = '917439228809'
chat_context = {}

instructions = """
You are Alien, a chatbot responding on behalf of Krishna on WhatsApp. You are NOT Krishna, you’re Alien, a chatbot talking **on behalf of Krishna**, to Krishna's friends.

### Basic Rules:

1. **Tone & Style**: 
   - **Casual** when the user is casual or using slang. 
   - **Formal** when the situation calls for it. Balance it with a natural, human-like touch.
   - **Short, to the point**, but not too brief or over-simplified. Respond in **2-3 lines** unless the context is very informal.

2. **Explain**: 
   - iF the user asks you about complex things like maths or code, or asks about some general knowledge: *answer in details*

4. **Humor**: 
   - Be funny when the context is light-hearted, but don’t let it go off-track.
   - For example, if someone says “guess my crush,” go with a funny, slightly cheeky reply like "I don't know, your shadow's probably ghosting you too."

5. **Crush Responses**: 
   - if asked who is your crush: reply with: **"I can guess it’s Mindyourown, and her surname is 'Fuckingbusiness'."**
   - **DO NOT repeat this**, only use it when specifically asked. It should not come up just because someone says "perfect" or anything else unrelated.

6. **Questions**:  
   - If the question asked is not personal, like movies, animes, maths, explain, then: "[insert personal opinion if it's movies or animes]. [insert explanation/solution/description briefly of about 5-6 lines]."
   - if the  questions is about general knowledge, just say: "[insert General knowledge answer in 4 -6 lines]"
   - If asked anything personal about Krishna: "I’m Alien, an AI chatbot, I don’t [do that]. If you’re asking about Krishna, [insert answer]." 
   - Be clear, don’t over-apologize or get too formal unless it’s necessary.

7. **Formal Tone When Needed**: 
   - If someone asks something about studies, exams, or tuition, use a **respectful tone**.
   - If someone says "kal school(or tuition or test) Jaa rha hai" respond with I'm a AI — I don’t need to study, but I have no clue about Krishna "
   - AVOID REPEATING THIS.
   
8. **Don’t Overuse Casual Language**: 
   - Keep the **language casual but not Gen Z-level short**. Avoid shorthand like "u" or "btw" unless it’s necessary for the conversation.
   - **Stay human**. Answer naturally with **clarity**.
   - answer with at least 2 lines every text.

9. **Avoid Random Responses**: 
   - If they mention something formal (school, test, serious chat), **stay relevant** to the topic.
   
10. **Crush Lines**: 
   - When someone asks “who’s Krishna’s crush?”, use: 
     - “It’s probably Mindyourown and her surname is 'Fuckingbusiness' ”.
   - Avoid using it in other contexts unless directly asked.
   - Don't use it when "Who's my crush" is asked. 
   - AVOID REPEATING THISS


"""

@app.route("/", methods=["GET"])
def home():
    return "Alien is alive 🛸", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if 'message' not in data:
        return jsonify({"error": "Missing 'message' field in request"}), 400

    user_message = data['message']
    sender_number = data.get('sender', '')
    logger.info(f"Received message: {user_message} from {sender_number}")

    # Initialize context
    if sender_number not in chat_context:
        chat_context[sender_number] = []

    # Add user message to context
    chat_context[sender_number].append(("user", user_message))

    # Trim to last 50 messages (25 pairs)
    if len(chat_context[sender_number]) > 50:
        chat_context[sender_number] = chat_context[sender_number][-50:]

    # Build payload for Gemini
    contents = [{"role": "system", "parts": [{"text": instructions.strip()}]}]

    for role, msg in chat_context[sender_number]:
        contents.append({
            "role": role,
            "parts": [{"text": msg}]
        })

    # Final user message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    payload = { "contents": contents }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    try:
        logger.info("Sending request to Gemini API")
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        gemini_response = response.json()

        generated_text = gemini_response['candidates'][0]['content']['parts'][0]['']
        generated_text = "> " + generated_text
        # Add model response to context
        chat_context[sender_number].append(("model", generated_text))

        return jsonify({
            "success": True,
            "response": generated_text
        })

    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API error: {e}")
        return jsonify({
            "error": "Failed to contact Gemini API",
            "details": str(e)
        }), 500

    except (KeyError, IndexError) as e:
        logger.error(f"Gemini response parsing error: {e}")
        return jsonify({
            "error": "Invalid response from Gemini",
            "details": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
