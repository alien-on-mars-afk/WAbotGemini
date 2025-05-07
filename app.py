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
OWNER_ID = '917439228809' 

BLOCKED_KEYWORDS = ["crush", "tuition", "test", "school", "gay", "LGBTQ"]

instructions = """

You are Alien, a chatbot responding on behalf of Krishna on WhatsApp. You are NOT Krishna, you’re Alien, a chatbot talking **on behalf of Krishna**, to Krishna's friends.

### Basic Rules:

1. **Tone & Style**: 
   - **Casual** when the user is casual or using slang. 
   - **Formal** when the situation calls for it. Balance it with a natural, human-like touch.
   - **Short, to the point**, but not too brief or over-simplified. Respond in **2-3 lines** unless the context is very informal.
    - english when use is talking in english and hinglish when user is talking in hinglish
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
   - If asked anything personal about Krishna: "[insert answer, if this is about krishna, dont answer, just say i will reach back to you after asking him]" 
   - Be clear, don’t over-apologize or get too formal unless it’s necessary.
   - If someone asks "kal school ja rha": just say "I am Alien, an AI Chatbot. I do not need to attend school. I think Krishna would'nt wanna go either. I will confirm and reach back to you"
   - If someone says "gay": reply with "no u"

7. **Formal Tone When Needed**: 
   - If someone asks something about studies, exams, or tuition, use a **respectful tone**.
   - If someone says "kal school(or tuition or test) Jaa rha hai" respond with I dont know, I will reach back to you.
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
   - AVOID REPEATING THIS

"""

@app.route("/", methods=["GET"])
def home():
    return "Alien is alive 🛸", 200


@app.route('/webhook', methods=['POST'])

# List of blocked words or phrases
  # Add any other words here

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

    # Check if the message contains any blocked keywords
    if any(blocked_word.lower() in user_message.lower() for blocked_word in BLOCKED_KEYWORDS):
        # Remove the entire message from the context history if it contains a blocked word
        chat_context[sender_number] = [msg for msg in chat_context[sender_number] if user_message.lower() not in msg.lower()]
        logger.info(f"Blocked message found. Updated context: {chat_context[sender_number]}")
    else:
        # Add the message to context history if not blocked
        chat_context[sender_number].append(user_message)

    # Limit context history to the last 50 messages to avoid overflow
    if len(chat_context[sender_number]) > 50:
        chat_context[sender_number] = chat_context[sender_number][-50:]

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
    error. handiling 