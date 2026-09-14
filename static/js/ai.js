let currentChatId = null;
let selectedFile = null;

document.addEventListener("DOMContentLoaded", () => {
    loadChatList();
    setupTextareaAutoResize();
    startNewChat();
});

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('hidden');
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    selectedFile = file;
    
    document.getElementById('file-name-display').textContent = file.name;
    document.getElementById('file-preview-container').classList.remove('hidden');
}

function removeAttachedFile() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('file-preview-container').classList.add('hidden');
}

async function loadChatList() {
    try {
        const res = await fetch('/api/chats');
        const chats = await res.json();
        const listEl = document.getElementById('chat-list');
        listEl.innerHTML = '';

        if (chats.length === 0) {
            listEl.innerHTML = '<div class="text-slate-500 text-center py-4 text-xs">No past chats</div>';
            return;
        }

        chats.forEach(chat => {
            const isSelected = chat.id === currentChatId;
            const item = document.createElement('div');
            item.className = `group flex items-center justify-between w-full px-3 py-2 rounded-xl transition ${isSelected ? 'bg-slate-800 text-white font-medium' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'}`;
            
            const titleBtn = document.createElement('button');
            titleBtn.className = 'flex-grow text-left truncate text-xs flex items-center space-x-2 focus:outline-none';
            titleBtn.innerHTML = `<i class="fa-regular fa-message opacity-70"></i> <span class="truncate">${escapeHTML(chat.title)}</span>`;
            titleBtn.onclick = () => loadChat(chat.id);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 p-1 transition focus:outline-none';
            deleteBtn.innerHTML = '<i class="fa-solid fa-trash-can text-xs"></i>';
            deleteBtn.title = "Delete chat";
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                deleteChat(chat.id);
            };

            item.appendChild(titleBtn);
            item.appendChild(deleteBtn);
            listEl.appendChild(item);
        });
    } catch (e) {
        console.error("Failed to load chat history", e);
    }
}

async function deleteChat(chatId) {
    try {
        await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
        if (currentChatId === chatId) {
            startNewChat();
        } else {
            loadChatList();
        }
    } catch (e) {
        console.error("Failed to delete chat", e);
    }
}

async function startNewChat() {
    try {
        const res = await fetch('/api/chats', { method: 'POST' });
        const data = await res.json();
        currentChatId = data.chat_id;
        document.getElementById('chat-messages').innerHTML = `
            <div class="max-w-3xl mx-auto flex space-x-4 items-start">
                <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white flex-shrink-0 shadow-md">
                    <i class="fa-solid fa-robot text-xs"></i>
                </div>
                <div class="bg-slate-900 border border-slate-800 p-4 rounded-2xl text-slate-300 leading-relaxed shadow-md space-y-2">
                    <p class="font-bold text-blue-400 font-mono text-xs">Nova AI</p>
                    <p>New chat session started. How can I assist you today?</p>
                </div>
            </div>
        `;
        loadChatList();
    } catch (e) {
        console.error("Failed to create chat", e);
    }
}

async function loadChat(chatId) {
    currentChatId = chatId;
    try {
        const res = await fetch(`/api/chats/${chatId}`);
        const messages = await res.json();
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';

        messages.forEach(msg => {
            appendMessage(msg.role === 'user' ? 'You' : 'Nova AI', msg.content, msg.role === 'user');
        });
        loadChatList();
    } catch (e) {
        console.error("Failed to load messages", e);
    }
}

const form = document.getElementById('chat-form');
const input = document.getElementById('chat-input');

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
    }
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text && !selectedFile) return;

    let displayMessage = text;
    if (selectedFile) {
        displayMessage += `<br><span class="inline-flex items-center space-x-1 text-xs bg-slate-800 border border-slate-700 px-2 py-1 rounded mt-1 text-blue-300"><i class="fa-solid fa-file"></i><span>${escapeHTML(selectedFile.name)}</span></span>`;
    }

    input.value = '';
    input.style.height = 'auto';

    const formData = new FormData();
    formData.append("chat_id", currentChatId);
    formData.append("message", text);
    if (selectedFile) {
        formData.append("file", selectedFile);
    }

    removeAttachedFile();
    appendMessage('You', displayMessage, true, true);

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.chat_id) currentChatId = data.chat_id;

        appendMessage('Nova AI', data.reply || data.error, false);
        loadChatList();
    } catch (e) {
        appendMessage('Nova AI', 'Error connecting to server.', false);
    }
});

function appendMessage(sender, text, isUser, isHtml = false) {
    const container = document.getElementById('chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'max-w-3xl mx-auto flex space-x-4 items-start';

    const avatarBg = isUser ? 'bg-purple-600' : 'bg-blue-600';
    const icon = isUser ? 'fa-user' : 'fa-robot';
    
    const parsedContent = isUser ? (isHtml ? text : escapeHTML(text)) : marked.parse(text);

    wrapper.innerHTML = `
        <div class="w-8 h-8 rounded-full ${avatarBg} flex items-center justify-center text-white flex-shrink-0 shadow-md">
            <i class="fa-solid ${icon} text-xs"></i>
        </div>
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-2xl text-slate-300 leading-relaxed shadow-md space-y-2 flex-grow">
            <p class="font-bold ${isUser ? 'text-purple-400' : 'text-blue-400'} font-mono text-xs">${sender}</p>
            <div class="markdown-body text-slate-200 text-sm space-y-2">${parsedContent}</div>
        </div>
    `;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;

    if (!isUser) {
        renderMathInElement(wrapper, {
            delimiters: [{left: "$$", right: "$$", display: true}, {left: "$", right: "$", display: false}],
            throwOnError: false
        });
    }
}

function setupTextareaAutoResize() {
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = input.scrollHeight + 'px';
    });
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}