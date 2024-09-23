let ws;
let typing = false;
let typingTimeout;

function connect(username, room) {
    ws = new WebSocket("ws://" + location.host + "/ws/" + encodeURIComponent(room) + "/" + encodeURIComponent(username));
    ws.onmessage = function(event) {
        let data = JSON.parse(event.data);
        if (data.event === "message") {
            displayMessage(data.message);
        } else if (data.event === "user_list") {
            updateUserList(data.users);
        } else if (data.event === "typing") {
            displayTypingStatus(data.username, data.typing);
        } else if (data.event === "history") {
            data.messages.forEach(displayMessage);
        }
    };
    ws.onclose = function() {
        alert("Savienojums ar serveri tika pārtraukts");
        document.getElementById("input").disabled = true;
        document.getElementById("send").disabled = true;
    };
}

function sendMessage() {
    let input = document.getElementById("input");
    let message = input.value.trim();
    if (message) {
        ws.send(JSON.stringify({
            "event": "message",
            "message": message
        }));
        input.value = '';
    }
}

function displayMessage(messageData) {
    let chat = document.getElementById('chat');
    let msgDiv = document.createElement('div');
    let timestampSpan = document.createElement('span');
    timestampSpan.classList.add('text-muted');
    timestampSpan.textContent = `[${messageData.timestamp}] `;

    msgDiv.appendChild(timestampSpan);

    if (messageData.is_system) {
        let contentSpan = document.createElement('span');
        contentSpan.classList.add('fst-italic', 'text-info');
        contentSpan.textContent = messageData.content;
        msgDiv.appendChild(contentSpan);
    } else {
        let usernameSpan = document.createElement('span');
        usernameSpan.classList.add('fw-bold');
        usernameSpan.textContent = `${messageData.username}: `;

        let contentSpan = document.createElement('span');
        contentSpan.textContent = messageData.content;

        msgDiv.appendChild(usernameSpan);
        msgDiv.appendChild(contentSpan);
    }

    chat.appendChild(msgDiv);
    chat.scrollTop = chat.scrollHeight;
}

function updateUserList(users) {
    let userList = document.getElementById('user_list');
    userList.innerHTML = '';
    users.forEach(function(user) {
        let li = document.createElement('li');
        li.textContent = user;
        li.classList.add('list-group-item', 'bg-secondary', 'text-white');
        userList.appendChild(li);
    });
}

function displayTypingStatus(userNickname, isTyping) {
    let typingElement = document.getElementById('typing');
    if (isTyping && userNickname !== username) {
        typingElement.textContent = `${userNickname} raksta...`;
    } else {
        typingElement.textContent = '';
    }
}

function userIsTyping() {
    if (!typing) {
        typing = true;
        ws.send(JSON.stringify({ "event": "typing", "typing": true }));
    }
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(stopTyping, 3000);
}

function stopTyping() {
    typing = false;
    ws.send(JSON.stringify({ "event": "typing", "typing": false }));
}

// Šeit veicam izmaiņas: nomainām 'keypress' uz 'keydown' un pievienojam 'event.preventDefault()'
document.getElementById("input").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Novērš noklusējuma darbību
        sendMessage();
    } else {
        userIsTyping();
    }
});
