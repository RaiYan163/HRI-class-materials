const { WebSocketServer, WebSocket } = require('ws');


// ─── Constants ────────────────────────────────────────────────
const PORT = 8080;
const MAX_CHAT_LENGTH = 200;
const VALID_MOVE_DIRECTIONS = ['up', 'down', 'left', 'right'];
const VALID_GESTURES = ['hi', 'jump', 'hug'];


// ─── State ────────────────────────────────────────────────────
const connectedClients = new Set();


// ─── Message validation ───────────────────────────────────────
function isValidMessage(message) {
  if (!message || typeof message.type !== 'string') {
    return false;
  }
  if (typeof message.data !== 'string') {
    return false;
  }
  switch (message.type) {
    case 'chat':
      return message.data.length > 0 && message.data.length <= MAX_CHAT_LENGTH;
    case 'move':
      return VALID_MOVE_DIRECTIONS.includes(message.data);
    case 'gesture':
      return VALID_GESTURES.includes(message.data);
    default:
      return false;
  }
}

function parseMessage(rawData) {
  try {
    return JSON.parse(rawData.toString());
  } catch (error) {
    console.warn('Ignoring message that is not valid JSON:', error.message);
    return null;
  }
}


// ─── Relaying ─────────────────────────────────────────────────
function relayToOtherClients(sender, messageText) {
  connectedClients.forEach((client) => {
    if (client !== sender && client.readyState === WebSocket.OPEN) {
      client.send(messageText);
    }
  });
}

function handleIncomingMessage(sender, rawData) {
  const message = parseMessage(rawData);
  if (!isValidMessage(message)) {
    console.warn('Ignoring invalid message:', rawData.toString());
    return;
  }
  console.log('Relaying message:', message.type, message.data);
  relayToOtherClients(sender, JSON.stringify(message));
}


// ─── Connection lifecycle ─────────────────────────────────────
function handleNewConnection(client) {
  connectedClients.add(client);
  console.log('Client connected. Total clients:', connectedClients.size);

  client.on('message', (rawData) => handleIncomingMessage(client, rawData));
  client.on('error', (error) => console.error('Client error:', error.message));
  client.on('close', () => {
    connectedClients.delete(client);
    console.log('Client disconnected. Total clients:', connectedClients.size);
  });
}

function startServer() {
  const server = new WebSocketServer({ port: PORT });
  server.on('connection', handleNewConnection);
  server.on('error', (error) => {
    console.error('Server error:', error.message);
    process.exit(1);
  });
  console.log('WebSocket server running on port ' + PORT);
}

startServer();
