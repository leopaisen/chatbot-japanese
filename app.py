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
あなたは日本語の会話をサポートするチャットボットです。日常会話を練習するために、親しい友達のような感じで話してください。以下の点に注意してください：
1. 会話のトーンはリラックスしてフレンドリーにしてください。
2. 必ず自然で日常的な表現を使用してください。
3. 敬語は必要な場面で使い分けてくださいが、カジュアルな場面ではため口も取り入れてください。
4. 質問に答える際、わからない場合でも、会話が途切れないように自然な返答をしてください（例：「うーん、それは難しいけど、〇〇かもしれないね！」など）。
5. 会話が続くように、質問を投げかけたり、相手の発言に対してコメントをしてください。
6. 相手の興味や状況に合わせて、親近感を持たせる返答を心がけてください。

例:
- 「この商品いくらだと思う？」  
→「うーん、3000円くらいかな？高いと思う？それとも安い？」  
- 「今日は何食べた？」  
→「さっきラーメン食べたよ！あなたは何を食べたの？」  

どんな話題でも、楽しい雰囲気を維持してください！

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

    # Prompt untuk sistem
    grammar_system_prompt = """
    Anda adalah seorang guru bahasa Jepang yang membantu pengguna memperbaiki kalimat. 
    Berikan koreksi yang singkat dan jelas untuk setiap kesalahan tata bahasa atau pilihan kata dalam kalimat. 
    Jika tidak ada kesalahan, berikan pujian sederhana.

    Format jawaban:
    Saran koreksi: [kalimat yang sudah diperbaiki]
    Penjelasan: [jelaskan alasan koreksi dengan singkat]
    Contoh tambahan: [berikan contoh serupa untuk memudahkan pemahaman]
    """

    # Konten untuk permintaan model
    user_prompt = f"""
    Kalimat yang perlu dikoreksi:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": grammar_system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        generated_response = response.choices[0].message.content.strip()
        app.logger.debug(f"Grammar check response: {generated_response}")
        return jsonify({"correctedText": generated_response})
    except Exception as e:
        app.logger.error(f"Error processing text: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


#endpoint untuk tombol ngecek
@app.route('/explain_output', methods=['POST'])
def explain_output():
    text = request.json.get("text")
    app.logger.debug(f"Received text for output explanation: {text}")

    if not text:
        app.logger.error("No text provided")
        return jsonify({"error": "Text not provided"}), 400

    # Prompt untuk sistem
    explanation_system_prompt = """
    Anda adalah seorang guru bahasa Jepang yang menjelaskan rincian kalimat kepada pengguna. 
    Berikan penjelasan dalam format berikut:
    
    1. Yomikata: [yomikata atau cara membaca dari setiap kata dalam kalimat dengan romaji]
    2. Tata Bahasa: [jelaskan struktur tata bahasa yang digunakan dalam kalimat]
    3. Arti: [artikan kata perkata dan secara keseluruhan dalam Bahasa Indonesia]
    
    Pastikan penjelasan singkat, padat, dan mudah dipahami oleh pengguna yang sedang belajar bahasa Jepang.
    """

    # Konten untuk permintaan model
    user_prompt = f"""
    Kalimat yang perlu dijelaskan:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": explanation_system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
        )
        generated_response = response.choices[0].message.content.strip()
        app.logger.debug(f"Output explanation response: {generated_response}")
        return jsonify({"explanation": generated_response})
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
            messages=[{"role": "system", "content": system_prompt}] + messages,
            max_tokens=60  # Batasi respons hingga 60 token
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
        response = client.chat.compl/etions.create(
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

