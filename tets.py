def webhook():
if not request.is\_json:
logger.error("Request content type is not JSON")
return jsonify({"error": "Content-Type must be application/json"}), 400

```
data = request.get_json()

if 'message' not in data:
    logger.error("Missing 'message' field in request")
    return jsonify({"error": "Missing 'message' field in request"}), 400

user_message = data['message']
sender_number = data.get('sender', '')
logger.info(f"Received message: {user_message} from {sender_number}")

if sender_number not in chat_context:
    chat_context[sender_number] = []

# Handle blocked words and clean the context
if any(blocked_word.lower() in user_message.lower() for blocked_word in BLOCKED_KEYWORDS):
    # Remove the entire message from the context history if it contains a blocked word
    chat_context[sender_number] = [msg for msg in chat_context[sender_number] if user_message.lower() not in msg.lower()]
    logger.info(f"Blocked message found. Updated context: {chat_context[sender_number]}")
else:
    chat_context[sender_number].append(user_message)

# Limit context to last 7 messages to avoid overflow
if len(chat_context[sender_number]) > 14:
    chat_context[sender_number] = chat_context[sender_number][-7:]

logger.info(f"Current context for {sender_number}: {chat_context[sender_number]}")

# Start building the payload
contents = [{"role": "user", "parts": [{"text": instructions.strip()}]}]

# Add both user and model messages to the context
for i, msg in enumerate(chat_context[sender_number]):
    role = "user" if i % 2 == 0 else "model"
    contents.append({
        "role": role,
        "parts": [{"text": msg}]
    })

contents.append({
    "role": "user",
    "parts": [{"text": user_message}]  # Last user message for context
})

payload = {
    "contents": contents
}

try:
    # Send request to Gemini API
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    logger.info("Sending request to Gemini API")
    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    gemini_response = response.json()
    try:
        # Extract the model's generated response
        generated_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
        generated_text = "*➔* " + generated_text
        logger.info(f"Generated response: {generated_text[:100]}...")

        # Add the model's response to the chat context
        chat_context[sender_number].append(generated_text)

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
```
