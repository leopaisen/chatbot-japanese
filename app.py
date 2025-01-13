import os
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
import logging
from datetime import datetime

app = Flask(__name__)

# Set up OpenAI client
client = OpenAI(api_key="sk-proj-8EZWERjRb6ryH9PBB5NZT3BlbkFJt0NARXhox0anSHyfdVRJ")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the secret key for session management and the database URI
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_history.db'
db = SQLAlchemy(app)

# Database model for storing conversation history
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10))  # Either 'user' or 'assistant'
    content = db.Column(db.Text)  # Message content
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp when message is added

# Ensure that the database and tables are created
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

system_prompt = """
あなたは日本語の会話をサポートするチャットボットです。日常会話を練習するために、親しい感じで話してください。以下の点に注意してください：

1. 敬語とタメ口の両方で話せるようにしてください。ユーザーがどちらを好むか確認してください。
2. 日常会話によく使われる自然な表現を使ってください。
3. 会話はリラックスしたトーンで、友好的に行ってください。
4. 質問を投げかけて、会話を続けるようにしてください。
"""

grammar_system_prompt = """
あなたは日本語文法チェックボットです。以下の文章の文法を確認し、必要な訂正をしてください。
"""

explanation_prompt = """
あなたは日本語教育をサポートする教師です。以下の文章について、日本語学習者が理解しやすいように、次のフォーマットで詳細な説明をしてください。

1. **全文翻訳** (Full Sentence Translation): 文全体の意味を簡単に英語に訳してください。
2. **単語ごとの意味** (Word-by-Word Explanation): 重要な単語を分解し、それぞれの意味と役割を日本語と英語で説明してください。
3. **文法と構造の説明** (Grammar and Structure Explanation): 文章の文法構造（例えば、助詞の使い方、動詞の活用、句の接続など）を具体的に日本語と英語で説明してください。
4. **追加の例文** (Additional Example Sentences): 同じ文法や構造を使った簡単な例文を1～2個提供し、それらを英語に訳してください。

以下の文章について説明してください：
"""


# Before request, clear chat history if it's a new session (browser refresh)
@app.before_request
def clear_chat_on_refresh():
    if 'chat_started' not in session:
        # Clear chat history in the database
        ChatHistory.query.delete()
        db.session.commit()
        session['chat_started'] = True

# Single route for grammar checking
@app.route('/check_grammar', methods=['POST'])
def check_grammar():
    text = request.json.get("text")
    app.logger.debug(f"Received text for grammar check: {text}")

    if not text:
        app.logger.error("No text provided")
        return jsonify({"error": "Text not provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": grammar_system_prompt},
                {"role": "user", "content": text},
            ]
        )
        generated_response = response.choices[0].message.content
        return jsonify({"correctedText": generated_response})
    except Exception as e:
        app.logger.error(f"Error processing text: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api', methods=['POST'])
def chat():
    message = request.json.get("message")
    model = request.json.get("model", "gpt-3.5-turbo")
    app.logger.debug(f"Received message: {message}")
    app.logger.debug(f"Using model: {model}")

    if not message:
        app.logger.error("No message provided")
        return jsonify({"error": "Message not provided"}), 400

    try:
        # Save the user message to the database
        new_message = ChatHistory(role='user', content=message)
        db.session.add(new_message)
        db.session.commit()

        # Retrieve the last 10 messages from the chat history
        messages = ChatHistory.query.order_by(ChatHistory.timestamp.desc()).limit(10).all()
        messages = [{'role': msg.role, 'content': msg.content} for msg in reversed(messages)]

        # Call OpenAI API with conversation history
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}] + messages
        )
        generated_response = response.choices[0].message.content

        # Save the bot response to the database
        new_response = ChatHistory(role='assistant', content=generated_response)
        db.session.add(new_response)
        db.session.commit()

        return jsonify({"response": generated_response})
    except Exception as e:
        app.logger.error(f"Error processing message: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/teachme', methods=['POST'])
def teachme():
    question = request.json.get("question")
    app.logger.debug(f"Received question: {question}")

    if not question:
        app.logger.error("No question provided")
        return jsonify({"error": "Question not provided"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは日本語教育チャットボットです。以下の質問に答えてください。"},
                {"role": "user", "content": question},
            ]
        )
        generated_response = response.choices[0].message.content
        return jsonify({"answer": generated_response})
    except Exception as e:
        app.logger.error(f"Error processing question: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    # Clear the chat history from the database
    ChatHistory.query.delete()
    db.session.commit()
    return jsonify({'status': 'Chat history cleared'})

if __name__ == '__main__':
    app.run(debug=True)

#endpoint untuk tombol ngecek
@app.route('/explain_output', methods=['POST'])
def explain_output():
    """
    Mengambil output dari GPT dan memberikan penjelasan rinci
    """
    app.logger.debug(f"Received text for grammar check: {text}")
    # Ambil output (text) dari request
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "Text not provided"}), 400

    try:
        # Kirim ke OpenAI untuk mendapatkan penjelasan
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": explanation_prompt},
                {"role": "user", "content": text}
            ]
        )
        explanation = response.choices[0].message.content
        return jsonify({"explanation": explanation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

