const WS_URL = 'ws://127.0.0.1:8765';
let ws;

// Add a message to the chatbox
function appendMessage(text, className = '') {
    const messagesDiv = document.getElementById('messages');
    const p = document.createElement('p');
    p.textContent = text;
    if (className) {
        p.classList.add(className);
    } else {
        p.classList.add('standard-message');
    }
    messagesDiv.appendChild(p);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Setup and configure websocket
function connectWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onopen = (event) => {
        console.log('WebSocket connection opened:', event);
        const statusMessageP = document.getElementById('status-message');
        statusMessageP.textContent = 'Websocket connection opened.';
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received from server:', data);

        const statusMessageP = document.getElementById('status-message');
        const usernameInputDiv = document.getElementById('username-input');
        const usernameMaxLengthSpan = document.getElementById('username-max-length');
        const usernameField = document.getElementById('username-field');
        const groupInputDiv = document.getElementById('group-input');
        const groupSelect = document.getElementById('group-select');
        const chatInputDiv = document.getElementById('chat-input');

        switch (data.type) {
            case 'status':
                statusMessageP.textContent = data.message;
                break;
            case 'error':
                appendMessage(`ERROR: ${data.message}`, 'error-message');
                statusMessageP.textContent = `Error: ${data.message}`;
                break;
            case 'username_prompt':
                statusMessageP.textContent = '';
                usernameMaxLengthSpan.textContent = data.maxLength;
                usernameInputDiv.style.display = 'block';
                break;
            case 'username_status':
                if (data.status === 'VALID') {
                    appendMessage(`Username "${usernameField.value}" chosen.`, 'system-message');
                    usernameInputDiv.style.display = 'none';
                    statusMessageP.textContent = 'Username accepted. Retrieving Groups...';
                } else {
                    statusMessageP.textContent = `Username invalid, Try Again.`;
                }
                break;
            case 'group_prompt':
                statusMessageP.textContent = '';
                groupInputDiv.style.display = 'block';
                groupSelect.innerHTML = '';
                data.groups.forEach(groupName => {
                    const option = document.createElement('option');
                    option.value = groupName;
                    option.textContent = groupName;
                    groupSelect.appendChild(option);
                });
                break;
            case 'group_status':
                if (data.status === 'JOINED' || data.status === 'CREATED_JOINED') {
                    appendMessage(data.message, 'system-message');
                    groupInputDiv.style.display = 'none';
                    chatInputDiv.style.display = 'block';
                    statusMessageP.textContent = `You joined "${groupname}.`;
                } else {
                    statusMessageP.textContent = `Group status: ${data.status} - ${data.message}`;
                }
                break;
            case 'chat_ready':
                appendMessage(data.message, 'system-message');
                statusMessageP.textContent = 'Ready to chat!';
                break;
            case 'chat_message':
                let time = data.time ? new Date(data.time).toLocaleTimeString() + ' ' : '';
                appendMessage(`${time}${data.content}`);
                break;
        }
    };

    // Event handler voor wanneer de WebSocket-verbinding gesloten wordt
    ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event);
        appendMessage('Connection lost.', 'system-message');
        const statusMessageP = document.getElementById('status-message');
        statusMessageP.textContent = 'Connection lost, trying again in 5 seconds...';
        setTimeout(connectWebSocket, 5000);
    };

    // Event handler voor WebSocket-fouten
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        appendMessage('Er is een WebSocket-fout opgetreden.', 'system-message');
        const statusMessageP = document.getElementById('status-message'); // statusMessageP wordt hier opgezocht
        statusMessageP.textContent = 'Fout in verbinding. Zie console voor details.';
    };
}

// Set username
document.getElementById('set-username-button').addEventListener('click', () => {
    const usernameField = document.getElementById('username-field');
    const statusMessageP = document.getElementById('status-message');
    const username = usernameField.value.trim();
    if (username) {
        ws.send(JSON.stringify({ type: 'username_input', username: username }));
    } else {
        statusMessageP.textContent = "Usernames can't be empty.";
    }
});

// Join group
document.getElementById('join-group-button').addEventListener('click', () => {
    const groupSelect = document.getElementById('group-select');
    const joinGroupPasswordField = document.getElementById('join-group-password-field');
    const groupName = groupSelect.value;
    const password = joinGroupPasswordField.value;
    if (groupName) {
        ws.send(JSON.stringify({ type: 'group_action', action: 'join', groupName: groupName, password: password }));
    }
});

// Create group
document.getElementById('create-group-button').addEventListener('click', () => {
    const newGroupNameField = document.getElementById('new-group-name');
    const newGroupPasswordField = document.getElementById('new-group-password');
    const statusMessageP = document.getElementById('status-message');
    const groupName = newGroupNameField.value.trim();
    const password = newGroupPasswordField.value;
    if (groupName) {
        ws.send(JSON.stringify({ type: 'group_action', action: 'create', groupName: groupName, password: password }));
    } else {
        statusMessageP.textContent = "Group names can't be empty.";
    }
});

// Send message
document.getElementById('send-button').addEventListener('click', () => {
    const messageField = document.getElementById('message-field');
    const message = messageField.value.trim();
    if (message) {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        appendMessage(`${timeString} Jij: ${message}`, 'own-message');

        ws.send(JSON.stringify({ type: 'chat_message', content: message }));
        messageField.value = '';
    }
});

// Enter key clicks on sendButton
document.getElementById('message-field').addEventListener('keypress', (event) => {
    const sendButton = document.getElementById('send-button');
    if (event.key === 'Enter') {
        event.preventDefault();
        sendButton.click();
    }
});

// Start websocket
connectWebSocket();