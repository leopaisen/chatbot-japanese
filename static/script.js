let recognition;
let recognizing = false;
let synth = window.speechSynthesis;
let voices = [];
let selectedVoice;
let selectedModel = 'gpt-3.5-turbo'; // デフォルトのモデル
let lastUserMessage = ''; // 最後のユーザーのメッセージを保存
let lastBotResponse = ''; // 最後のボットの応答を保存

// 音声認識の初期化
function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('このブラウザでは音声認識がサポートされていません。');
        return;
    }
    recognition = new SpeechRecognition();
    recognition.lang = 'ja-JP'; // 言語を日本語に設定
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = function(event) {
        const messageInput = document.getElementById('message-input');
        const transcript = event.results[event.resultIndex][0].transcript;
        messageInput.value = transcript;
    };

    recognition.onerror = function(event) {
        console.error('音声認識エラー:', event.error);
    };

    recognition.onend = function() {
        if (recognizing) {
            recognition.start(); // 停止された場合は再開
        } else {
            document.getElementById('speech-btn').innerText = '🎤';
        }
    };
}

// 音声認識のオン/オフを切り替える
function toggleRecognition() {
    if (recognizing) {
        recognition.stop();
        recognizing = false;
        document.getElementById('speech-btn').innerText = '🎤';
    } else {
        recognition.start();
        recognizing = true;
        document.getElementById('speech-btn').innerText = '🛑';
    }
}

// ページ読み込み時に以前の会話をロード
async function loadPreviousConversation() {
    try {
        const response = await fetch('/api/get_chat_history');
        if (response.ok) {
            const data = await response.json();
            data.history.forEach(message => {
                displayMessage(message.content, message.role === 'user' ? 'user-message' : 'response-message');
            });
        }
    } catch (error) {
        console.error('チャット履歴の取得エラー:', error);
    }
}

// テキスト読み上げのために音声リストを取得
function populateVoiceList() {
    voices = synth.getVoices().filter(voice => voice.lang.startsWith('ja'));
    const voiceSelect = document.getElementById('voice-select');
    voiceSelect.innerHTML = '';

    if (voices.length === 0) {
        console.error("日本語の音声が見つかりません。");
        return;
    }

    voices.forEach((voice, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${voice.name} (${voice.lang})`;
        voiceSelect.appendChild(option);
    });

    selectedVoice = voices[0];
    voiceSelect.selectedIndex = 0;
}

// 音声選択時の処理
function handleVoiceChange(event) {
    selectedVoice = voices[event.target.value];
}

// ボットの応答をテキスト読み上げ
function speakMessage(message) {
    if (selectedVoice && message) {
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.voice = selectedVoice;
        synth.speak(utterance);
    }
}


// ユーザーのメッセージをチャットボットに送信する
async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const messageText = messageInput.value.trim();
    
    if (messageText === '') return;

    lastUserMessage = messageText; // lastUserMessageを更新
    console.log('lastUserMessage:', lastUserMessage);

    const modelSelect = document.getElementById('model-select');
    const selectedModel = modelSelect.value;
    const promptType = modelSelect.options[modelSelect.selectedIndex].dataset.prompt; // promptTypeを取得

    displayMessage(messageText, 'user-message');

    try {
        const response = await fetch('/api', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: messageText, model: selectedModel, promptType: promptType })
        });
        if (!response.ok) {
            throw new Error(`HTTPエラー! ステータス: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.response) {
            lastBotResponse = data.response; // 応答を更新
            console.log('lastBotResponse:', lastBotResponse); // デバッグ用
            displayMessage(data.response, 'response-message');
            speakMessage(data.response);
        } else {
            displayMessage('サーバーからの応答がありません', 'response-message');
        }
    } catch (error) {
        displayMessage('エラー: ' + error.message, 'response-message');
    }
    messageInput.value = '';
}

// チャット履歴をクリアする
async function clearChat() {
    try {
        const response = await fetch('/clear_chat', { method: 'POST' });
        if (response.ok) {
            document.getElementById('chat-box').innerHTML = '';
            alert('チャット履歴がクリアされました');
        } else {
            alert('チャット履歴のクリアに失敗しました');
        }
    } catch (error) {
        alert('エラー: ' + error.message);
    }
}

// チャットボックスにメッセージを表示する
function displayMessage(message, className) {
    const chatBox = document.getElementById('chat-box');
    const messageElement = document.createElement('div');
    messageElement.className = 'message ' + className;
    messageElement.textContent = message;
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// 最後のユーザーのメッセージの文法をチェックする
async function checkLastUserMessageGrammar() {
    if (lastUserMessage === '') return;
    await checkChatGrammar(lastUserMessage);
}

// 文法チェック機能
async function checkChatGrammar(text) {
    try {
        const response = await fetch('/check_grammar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) {
            throw new Error(`HTTPエラー! ステータス: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.correctedText) {
            if (data.correctedText === text) {
                displayGrammarCorrection('テキストは正しいです!');
            } else {
                displayGrammarCorrection(`${data.correctedText}`);
            }
        } else {
            displayGrammarCorrection('修正の提案はありません。');
        }
    } catch (error) {
        console.error('文法チェックエラー:', error);
        displayGrammarCorrection('文法チェック中にエラーが発生しました。');
    }
}



function showCorrectSign() {
    const correctSign = document.getElementById('correct-sign');
    if (correctSign) {
        correctSign.style.display = 'inline';
    }
}

function hideCorrectSign() {
    const correctSign = document.getElementById('correct-sign');
    if (correctSign) {
        correctSign.style.display = 'none';
    }
}

// 文法訂正を表示する
function displayGrammarCorrection(message) {
    const correctionsBox = document.getElementById('grammar-corrections');
    correctionsBox.innerHTML = ''; // 以前の訂正内容をクリア

    // メッセージを改行（\n）で区切ってリスト化
    const lines = message.split('\n');

    lines.forEach((line, index) => {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        messageElement.style.textAlign = 'left'; // 左寄せ
        messageElement.style.marginBottom = '5px'; // ポイント間のスペースを追加
        messageElement.textContent = `${index + 1}. ${line.trim()}`; // 番号を追加
        correctionsBox.appendChild(messageElement);
    });
}

// 最後のチャットボットの出力を説明する
async function explainLastBotOutput() {
    if (!lastBotResponse) {
        console.error('ボットの出力が見つかりません。');
        displayExplanation('<p style="color: red;">出力が見つかりません。</p>');
        return;
    }

    try {
        const response = await fetch('/explain_output', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: lastBotResponse })
        });

        if (!response.ok) {
            throw new Error(`HTTPエラー! ステータス: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.explanation) { // data.explanationを使用
            displayExplanation(`<p>${data.explanation}</p>`);
        } else {
            displayExplanation('<p style="color: red;">説明を生成できませんでした。</p>');
        }

    } catch (error) {
        console.error('出力の説明中にエラーが発生:', error);
        displayExplanation(`<p style="color: red;">エラー: ${error.message}</p>`);
    }
}

// 文法訂正ボックスに説明を表示する
function displayExplanation(content) {
    const explanationBox = document.getElementById('grammar-corrections');
    explanationBox.innerHTML = `
        <div class="message response-message">${content}</div>
    `;
}

// イベントリスナーを設定する
document.getElementById('voice-select').addEventListener('change', handleVoiceChange);
document.getElementById('model-select').addEventListener('change', (event) => {
    selectedModel = event.target.value;
});

document.addEventListener('DOMContentLoaded', () => {
    initRecognition();
    if (synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = populateVoiceList;
    } else {
        populateVoiceList();
    }
    loadPreviousConversation();
});

// 出力説明を表示する
function displayOutputExplanation(message) {
    const explanationsBox = document.getElementById('output-explanations'); // アウトプットチェック用のコンテナID
    explanationsBox.innerHTML = ''; // 以前の説明をクリア

    // メッセージを改行（\n）で区切ってリスト化
    const lines = message.split('\n');

    lines.forEach((line, index) => {
        const messageElement = document.createElement('div');
        messageElement.className = 'message response-message';
        messageElement.style.textAlign = 'left'; 
        messageElement.style.marginBottom = '5px'; 
        messageElement.style.backgroundColor = '#f8d7da'; 
        messageElement.style.color = '#000000'; 
        messageElement.style.padding = '10px'; 
        messageElement.style.borderRadius = '5px'; 
        messageElement.textContent = `${index + 1}. ${line.trim()}`; 
        explanationsBox.appendChild(messageElement);
    });
}



