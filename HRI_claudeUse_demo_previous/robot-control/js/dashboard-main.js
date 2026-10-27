// ─── Constants ────────────────────────────────────────────────
const NOT_CONNECTED_MESSAGE = 'Not connected to the server. Retrying...';
const ERROR_DISPLAY_MS = 3000;


// ─── State ────────────────────────────────────────────────────
let socket = null;
let errorTimeoutId = null;


// ─── Element lookups ──────────────────────────────────────────
function getMessageInput() {
  return document.getElementById('message-input');
}

function getChatLog() {
  return document.getElementById('chat-log');
}


// ─── UI updates ───────────────────────────────────────────────
function setConnectionStatus(isConnected) {
  const badge = document.getElementById('connection-status');
  badge.textContent = isConnected ? 'Connected' : 'Disconnected';
  badge.classList.toggle('status-connected', isConnected);
  badge.classList.toggle('status-disconnected', !isConnected);
}

function showErrorMessage(text) {
  const errorElement = document.getElementById('error-message');
  errorElement.textContent = text;
  errorElement.hidden = false;
  clearTimeout(errorTimeoutId);
  errorTimeoutId = setTimeout(() => {
    errorElement.hidden = true;
  }, ERROR_DISPLAY_MS);
}

function appendChatEntry(text) {
  const chatLog = getChatLog();
  const entry = document.createElement('div');
  entry.className = 'chat-entry';
  entry.textContent = text; // textContent keeps user input from becoming HTML
  chatLog.appendChild(entry);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function clearMessageInput() {
  getMessageInput().value = '';
}


// ─── WebSocket ────────────────────────────────────────────────
function isSocketOpen() {
  return socket !== null && socket.readyState === WebSocket.OPEN;
}

function sendCommand(type, data) {
  if (!isSocketOpen()) {
    showErrorMessage(NOT_CONNECTED_MESSAGE);
    return false;
  }
  socket.send(JSON.stringify({ type, data }));
  return true;
}

function connectToServer() {
  socket = new WebSocket(SERVER_URL);
  socket.onopen = () => setConnectionStatus(true);
  socket.onerror = (error) => console.error('WebSocket error:', error);
  socket.onclose = () => {
    setConnectionStatus(false);
    setTimeout(connectToServer, RECONNECT_DELAY_MS);
  };
}


// ─── Event handlers ───────────────────────────────────────────
function handleChatSubmit(event) {
  event.preventDefault();
  const messageText = getMessageInput().value.trim();
  if (messageText.length === 0) {
    return;
  }
  if (sendCommand('chat', messageText)) {
    appendChatEntry(messageText);
    clearMessageInput();
  }
}

function handleMoveClick(event) {
  sendCommand('move', event.currentTarget.dataset.direction);
}

function handleGestureClick(event) {
  sendCommand('gesture', event.currentTarget.dataset.gesture);
}

function attachEventListeners() {
  document.getElementById('chat-form')
    .addEventListener('submit', handleChatSubmit);
  document.querySelectorAll('[data-direction]').forEach((button) => {
    button.addEventListener('click', handleMoveClick);
  });
  document.querySelectorAll('[data-gesture]').forEach((button) => {
    button.addEventListener('click', handleGestureClick);
  });
}


// ─── Startup ──────────────────────────────────────────────────
attachEventListeners();
connectToServer();
