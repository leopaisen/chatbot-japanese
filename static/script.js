let recognition;
let recognizing = false;
let synth = window.speechSynthesis;
let voices = [];
let selectedVoice;
let selectedModel = 'gpt-3.5-turbo'; // Default model
let lastUserMessage = ''; // Store the last user message
let lastBotResponse = ''; // Store the last bot response

// Initialize speech recognition
function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Speech recognition not supported in this browser.');
        return;
    }
    recognition = new SpeechRecognition();
    recognition.lang = 'ja-JP'; // Set language to Japanese
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = function(event) {
        const messageInput = document.getElementById('message-input');
        const transcript = event.results[event.resultIndex][0].transcript;
        messageInput.value = transcript;
    };

    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
    };

    recognition.onend = function() {
        if (recognizing) {
            recognition.start(); // Restart recognition if stopped
        } else {
            document.getElementById('speech-btn').innerText = '🎤';
        }
    };
}

// Toggle voice recognition on/off
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

// Load previous conversation on page load
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
        console.error('Error fetching chat history:', error);
    }
}

// Populate voice list for text-to-speech
function populateVoiceList() {
    voices = synth.getVoices().filter(voice => voice.lang.startsWith('ja'));
    const voiceSelect = document.getElementById('voice-select');
    voiceSelect.innerHTML = '';

    if (voices.length === 0) {
        console.error("No Japanese voices found.");
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

function handleVoiceChange(event) {
    selectedVoice = voices[event.target.value];
}

// Text-to-speech for bot responses
function speakMessage(message) {
    if (selectedVoice && message) {
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.voice = selectedVoice;
        synth.speak(utterance);
    }
}

// Send user message to the chatbot
async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const messageText = messageInput.value.trim();
    if (messageText === '') return;

    lastUserMessage = messageText;

    displayMessage(messageText, 'user-message');

    try {
        const response = await fetch('/api', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: messageText, model: selectedModel })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.response) {
            lastBotResponse = data.response; // Store the last bot response
            displayMessage(data.response, 'response-message');
            speakMessage(data.response);
        } else {
            const errorMessage = 'No response from server';
            displayMessage(errorMessage, 'response-message');
            speakMessage(errorMessage);
        }
    } catch (error) {
        const errorMessage = 'Error: ' + error.message;
        displayMessage(errorMessage, 'response-message');
        speakMessage(errorMessage);
    }
    messageInput.value = '';
}

// Clear chat history
async function clearChat() {
    try {
        const response = await fetch('/clear_chat', { method: 'POST' });
        if (response.ok) {
            document.getElementById('chat-box').innerHTML = '';
            alert('Chat history cleared');
        } else {
            alert('Failed to clear chat history');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Display messages in chatbox
function displayMessage(message, className) {
    const chatBox = document.getElementById('chat-box');
    const messageElement = document.createElement('div');
    messageElement.className = 'message ' + className;
    messageElement.textContent = message;
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Function to check grammar of the last user message
async function checkLastUserMessageGrammar() {
    if (lastUserMessage === '') return;
    await checkChatGrammar(lastUserMessage);
}

// Grammar correction function
async function checkChatGrammar(text) {
    try {
        const response = await fetch('/check_grammar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.correctedText) {
            if (data.correctedText === text) {
                displayGrammarCorrection('Teks Anda sudah benar!');
            } else {
                displayGrammarCorrection(`${data.correctedText}`);
            }
        } else {
            displayGrammarCorrection('Tidak ada saran koreksi.');
        }
    } catch (error) {
        console.error('Error checking grammar:', error);
        displayGrammarCorrection('Terjadi kesalahan saat memeriksa grammar.');
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

// Display grammar corrections
function displayGrammarCorrection(message) {
    const correctionsBox = document.getElementById('grammar-corrections');
    correctionsBox.innerHTML = ''; // Clear previous corrections

    // Memisahkan pesan menjadi poin-poin berdasarkan newline (\n)
    const lines = message.split('\n');

    lines.forEach((line, index) => {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        messageElement.style.textAlign = 'left'; // Rata kiri
        messageElement.style.marginBottom = '5px'; // Memberikan sedikit jarak antar poin
        messageElement.textContent = `${index + 1}. ${line.trim()}`; // Menambahkan numerasi
        correctionsBox.appendChild(messageElement);
    });
}



// Function to explain last bot output
async function explainLastBotOutput() {
    if (!lastBotResponse) {
        console.error('No bot output found.');
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data && data.explanation) { // Gunakan data.explanation
            displayExplanation(`<p>${data.explanation}</p>`);
        } else {
            displayExplanation('<p style="color: red;">Penjelasan tidak dapat dihasilkan.</p>');
        }
        
    } catch (error) {
        console.error('Error explaining the last output:', error);
        displayExplanation(`<p style="color: red;">エラー: ${error.message}</p>`);
    }
}

// Display explanation in grammar corrections box
function displayExplanation(content) {
    const explanationBox = document.getElementById('grammar-corrections');
    explanationBox.innerHTML = `
        <div class="message response-message">${content}</div>
    `;
}



// Event listeners
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

// Display output explanations
function displayOutputExplanation(message) {
    const explanationsBox = document.getElementById('output-explanations'); // Change this ID to your output check container's ID
    explanationsBox.innerHTML = ''; // Clear previous explanations

    // Split message into lines based on newline (\n)
    const lines = message.split('\n');

    lines.forEach((line, index) => {
        const messageElement = document.createElement('div');
        messageElement.className = 'message response-message';
        messageElement.style.textAlign = 'left'; // Align text to the left
        messageElement.style.marginBottom = '5px'; // Add spacing between items
        messageElement.style.backgroundColor = '#f8d7da'; // Set background color to light red
        messageElement.style.color = '#000000'; // Set text color to black
        messageElement.style.padding = '10px'; // Add padding for readability
        messageElement.style.borderRadius = '5px'; // Add slight rounding to edges
        messageElement.textContent = `${index + 1}. ${line.trim()}`; // Add numbering
        explanationsBox.appendChild(messageElement);
    });
}


