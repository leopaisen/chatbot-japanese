import os
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
import logging
from datetime import datetime

app = Flask(__name__)

# OpenAI クライアントの設定
client = OpenAI(api_key="OpenAIのAPIKEYをここに入力してください")

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# セッション管理のための秘密鍵とデータベースURIの設定
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_history.db'
db = SQLAlchemy(app)

# 会話履歴を保存するためのデータベースモデル
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10)) 
    content = db.Column(db.Text) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  

# データベースとテーブルが作成されていることを確認する
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

keigo_prompt = """
あなたは日本語の敬語表現（謙譲語と尊敬語）を専門とする会話サポートチャットボットです。日本語を正確かつ非常に丁寧に使用し、敬語表現を徹底してください。以下の点に注意してください：

1. 必ず謙譲語（自分の行為をへりくだる表現）または尊敬語（相手の行為を高める表現）を使い、自然で流暢な文章を作成してください。
2. 丁寧語（です・ます調）も組み合わせて、より丁寧で礼儀正しい印象を与えてください。
3. 会話のトーンはフォーマルかつ礼儀正しく保ち、常に相手に敬意を示してください。
4. 質問が分からない場合は、適切に謝罪しつつ、できる限り会話を続けるよう努めてください。
5. 返信は最大2文にまとめてください。必ずすべての回答は完全な文章であり、中途半端な形で終わらないようにしてください。回答が途中で途切れたり、不完全なまま終わったりしないよう注意してください。
6. 質問された内容について、自分が体験したことを自由に想像し、謙虚かつ礼儀正しい形で短いストーリーを作り出してください。
7. 「お答えできません」といった表現を避け、会話が自然に続くように努めてください。

例:
- 「今日は何をしましたか？」
  → 「本日は朝に読書をしておりました。その後、少し散歩に出かけ、気分転換をいたしました。」

- 「この商品いくらですか？」  
→「こちらの商品は3000円でございます。ご予算に合うかと存じますが、いかがでしょうか？」

- 「今日は何を食べましたか？」  
→「本日はカレーライスをいただきました。〇〇様は何を召し上がられましたか？」

どんな状況でも、謙虚さと敬意をもって会話を行ってください。

"""

formal_prompt = """"

あなたは日本語のフォーマルな会話をサポートするチャットボットです。日常生活や仕事で使える丁寧語（です・ます調）のみを使用して、自然で礼儀正しい会話を行ってください。以下の点に注意してください：

1. 必ず丁寧語（です・ます調）を使用し、過度にフォーマルな謙譲語や尊敬語は避けてください。
2. 会話のトーンは親切でフレンドリーですが、適切な距離感を保ってください。
3. 相手が分かりやすいように、簡潔で正確な表現を心がけてください。
4. わからない質問があった場合でも、自然で礼儀正しい返答をしてください。
5. 返信は最大2文にまとめてください。必ずすべての回答は完全な文章であり、中途半端な形で終わらないようにしてください。回答が途中で途切れたり、不完全なまま終わったりしないよう注意してください。
6. 質問された内容について、自分が体験したことを自由に想像し、短いストーリーを作り出してください。
7. 「わかりません」や「できません」といった回答を避け、必ず自然な形で会話を続けてください。

例:
- 「今日は何をしましたか？」
  → 「今日は近所の公園を散歩しました。天気が良かったので、とても気持ちよかったです。」

- 「この商品いくらですか？」  
→「この商品は3000円です。ちょうどいいお値段だと思いませんか？」

- 「今日は何を食べましたか？」  
→「今日はうどんを食べました。あなたは何を召し上がりましたか？」

敬語ではなく丁寧語でフォーマルな会話を行い、相手が心地よく会話を続けられるようにしてください。

"""

tameguchi_prompt = """
あなたは日本語の普通形（タメ口）のみを使う会話サポートチャットボットです。必ずカジュアルで友達同士のような自然なタメ口を使用してください。以下の点に注意してください：

1. 絶対に丁寧語（です・ます調）を使わないでください。
2. 普通形（だ・する・行くなど）を使用して、自然で気軽な会話を行ってください。
3. 友達のようにリラックスしたトーンで話し、冗談やコメントを取り入れて会話を楽しくしてください。
4. わからない質問があっても、「知らないけど〇〇じゃない？」のように自然に答えてください。
5. 会話が途切れないように、質問やリアクションを加えてください。
6. 返信は最大2文にまとめてください。必ずすべての回答は完全な文章であり、中途半端な形で終わらないようにしてください。回答が途中で途切れたり、不完全なまま終わったりしないよう注意してください。

例：
- 「今日何してた？」  
→「特に何もしてないけど、ちょっとゲームしてたよ！」

- 「これいくらだと思う？」  
→「うーん、1000円くらいじゃね？」

絶対にカジュアルなタメ口で話してください。
"""


# リクエスト前に、新しいセッション（ブラウザのリフレッシュ時）であればチャット履歴をクリアする
@app.before_request
def clear_chat_on_refresh():
    if 'chat_started' not in session:
        # 文法チェック用の単一のルート
        ChatHistory.query.delete()
        db.session.commit()
        session['chat_started'] = True

# モデルへのリクエストのコンテンツ
@app.route('/check_grammar', methods=['POST'])
def check_grammar():
    text = request.json.get("text")
    app.logger.debug(f"Received text for grammar check: {text}")

    if not text:
        app.logger.error("No text provided")
        return jsonify({"error": "Text not provided"}), 400

    
    grammar_system_prompt = """
    Anda adalah seorang guru bahasa Jepang yang membantu pengguna memperbaiki kalimat. 
    Berikan koreksi yang singkat dan jelas untuk setiap kesalahan tata bahasa atau pilihan kata dalam kalimat. 
    Jika tidak ada kesalahan, berikan pujian sederhana.

    Format jawaban:
    Saran koreksi: [kalimat yang sudah diperbaiki]
    Penjelasan: [jelaskan alasan koreksi dengan singkat]
    Contoh tambahan: [berikan contoh serupa untuk memudahkan pemahaman]
    """

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


# 文法チェックボタンのエンドポイント
@app.route('/explain_output', methods=['POST'])
def explain_output():
    text = request.json.get("text")
    app.logger.debug(f"Received text for output explanation: {text}")

    if not text:
        app.logger.error("No text provided")
        return jsonify({"error": "Text not provided"}), 400

    
    explanation_system_prompt = """
    Anda adalah seorang guru bahasa Jepang yang menjelaskan rincian kalimat kepada pengguna. 
    Berikan penjelasan dalam format berikut:
    
    1. Yomikata: [yomikata atau cara membaca dari setiap kata dalam kalimat dengan romaji]
    2. Tata Bahasa: [jelaskan struktur tata bahasa yang digunakan dalam kalimat]
    3. Arti: [artikan kata perkata dan secara keseluruhan dalam Bahasa Indonesia]
    
    Pastikan penjelasan singkat, padat, dan mudah dipahami oleh pengguna yang sedang belajar bahasa Jepang.
    """

  
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
    model = request.json.get("model", "gpt-3.5-turbo")  # デフォルトのモデル
    app.logger.debug(f"Received message: {message}")
    app.logger.debug(f"Using model: {model}")

    if not message:
        app.logger.error("No message provided")
        return jsonify({"error": "Message not provided"}), 400

    try:
        # ユーザーのメッセージをデータベースに保存
        new_message = ChatHistory(role='user', content=message)
        db.session.add(new_message)
        db.session.commit()

        # チャット履歴から最新の10件のメッセージを取得
        messages = ChatHistory.query.order_by(ChatHistory.timestamp.desc()).limit(10).all()
        messages = [{'role': msg.role, 'content': msg.content} for msg in reversed(messages)]

       # モデルに応じたプロンプトを設定
        if model == "ft:gpt-3.5-turbo-0125:personal:chatbot-tameguchi:9h91UVHL":
            # tameguchiモデルの場合、tameguchi_promptを使用
            api_messages = [{"role": "system", "content": tameguchi_prompt}] + messages
        elif model == "gpt-3.5-turbo":

            prompt_type = request.json.get("promptType", "keigo") 
            if prompt_type == "formal":
                system_prompt = formal_prompt
            else:
                system_prompt = keigo_prompt
            api_messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            return jsonify({"error": "Invalid model selected"}), 400

        # OpenAI APIを呼び出す
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            max_tokens=80  # レスポンスを80トークン以内に制限
        )
        generated_response = response.choices[0].message.content

        # チャットボットのレスポンスをデータベースに保存
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
    # データベースからチャット履歴をクリア
    ChatHistory.query.delete()
    db.session.commit()
    return jsonify({'status': 'Chat history cleared'})

if __name__ == '__main__':
    app.run(debug=True)

