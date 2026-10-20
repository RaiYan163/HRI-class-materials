// ─── State ────────────────────────────────────────────────────
let socket = null;


// ─── UI updates ───────────────────────────────────────────────
function setConnectionStatus(isConnected) {
  const badge = document.getElementById('connection-status');
  badge.textContent = isConnected ? 'Connected' : 'Disconnected';
  badge.classList.toggle('status-connected', isConnected);
  badge.classList.toggle('status-disconnected', !isConnected);
}


// ─── Incoming messages ────────────────────────────────────────
function processMessage(message) {
  switch (message.type) {
    case 'chat':
      showSpeechBubble(message.data);
      break;
    case 'move':
      moveRobot(message.data);
      break;
    case 'gesture':
      doGesture(message.data);
      break;
    default:
      console.warn('Received message with unknown type:', message);
  }
}

function handleIncomingMessage(event) {
  try {
    const message = JSON.parse(event.data);
    if (!message.type) {
      console.warn('Received message with no type field:', message);
      return;
    }
    processMessage(message);
  } catch (error) {
    console.error('Failed to parse message:', error);
  }
}


// ─── WebSocket ────────────────────────────────────────────────
function connectToServer() {
  socket = new WebSocket(SERVER_URL);
  socket.onopen = () => setConnectionStatus(true);
  socket.onmessage = handleIncomingMessage;
  socket.onerror = (error) => console.error('WebSocket error:', error);
  socket.onclose = () => {
    setConnectionStatus(false);
    setTimeout(connectToServer, RECONNECT_DELAY_MS);
  };
}


// ─── Startup ──────────────────────────────────────────────────
placeRobotInCenter();
connectToServer();
