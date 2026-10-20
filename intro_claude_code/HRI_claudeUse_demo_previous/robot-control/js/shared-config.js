// Shared by dashboard and robot pages (loaded as a plain script).
const SERVER_URL = 'ws://localhost:8080';
// Retry so the pages recover if the server restarts
const RECONNECT_DELAY_MS = 2000;
