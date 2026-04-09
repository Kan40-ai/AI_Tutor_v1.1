import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request
from services.tutor_service import TutorService
from config import config as app_config
from core.rag import EduRAGConfig

app = Flask(__name__)

# 🟢 Initialize the AI config (this uses the defaults set in rag.py)
rag_config = EduRAGConfig()

# 🟢 CONFIGURATION HANDSHAKE
# Ensure we pass the key path and Pinecone API key from the environment/config
tutor_service = TutorService(
    config=rag_config,
    pinecone_api_key=os.environ.get("PINECONE_API_KEY"),
    google_creds_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "google_credentials.json")
)

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/api/chat", methods=["POST"])
async def chat():  # 🟢 Notice the 'async' keyword added here
    try:
        data = request.get_json() or {}
        message = data.get("message", "")

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # 🚀 CALL THE BACKEND (Awaiting the async function)
        # Notice we changed the method name to 'ask_tutor' and parameter to 'question'
        resp = await tutor_service.generate_answer(message)

        return jsonify({
            "answer": resp['answer'],
            "sources": resp["sources"],  # Double-check if your backend uses .context or .sources!
            "status": 'success'
        })

    except Exception as e:
        app.logger.error(f"Chat Error: {str(e)}")
        return jsonify({"error": "Tutor encountered an issue. Check backend logs.", "details": str(e)}), 500

if __name__ == "__main__":
    # Ensure environment variables are loaded if not using a .env file
    app.run(debug=True, port=5000, use_reloader=False)