// ─── Constants ────────────────────────────────────────────────
const MOVE_STEP_PX = 20;
const SPEECH_BUBBLE_MS = 3000;
const BUBBLE_FADE_MS = 400;
const WINDOW_MARGIN_PX = 8;

const MOVE_OFFSETS = {
  up: { top: -MOVE_STEP_PX, left: 0 },
  down: { top: MOVE_STEP_PX, left: 0 },
  left: { top: 0, left: -MOVE_STEP_PX },
  right: { top: 0, left: MOVE_STEP_PX }
};

// Which element gets which class, and how long the gesture lasts
const GESTURES = {
  hi: { className: 'gesture-hi', targetIds: ['arm-right'], durationMs: 1500 },
  jump: { className: 'gesture-jump', targetIds: ['robot'], durationMs: 600 },
  hug: {
    className: 'gesture-hug',
    targetIds: ['arm-left', 'arm-right'],
    durationMs: 2000
  }
};


// ─── State ────────────────────────────────────────────────────
const gestureTimeoutIds = {};


// ─── Movement ─────────────────────────────────────────────────
function clampToRange(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function placeRobotInCenter() {
  const robot = document.getElementById('robot');
  robot.style.left = (window.innerWidth - robot.offsetWidth) / 2 + 'px';
  robot.style.top = (window.innerHeight - robot.offsetHeight) / 2 + 'px';
}

function moveRobot(direction) {
  const offset = MOVE_OFFSETS[direction];
  if (!offset) {
    console.warn('Unknown move direction:', direction);
    return;
  }
  const robot = document.getElementById('robot');
  const maxLeft = window.innerWidth - robot.offsetWidth - WINDOW_MARGIN_PX;
  const maxTop = window.innerHeight - robot.offsetHeight - WINDOW_MARGIN_PX;
  const newLeft = robot.offsetLeft + offset.left;
  const newTop = robot.offsetTop + offset.top;
  robot.style.left = clampToRange(newLeft, WINDOW_MARGIN_PX, maxLeft) + 'px';
  robot.style.top = clampToRange(newTop, WINDOW_MARGIN_PX, maxTop) + 'px';
}


// ─── Gestures ─────────────────────────────────────────────────
function removeGestureClass(gesture) {
  gesture.targetIds.forEach((id) => {
    document.getElementById(id).classList.remove(gesture.className);
  });
}

function addGestureClass(gesture) {
  gesture.targetIds.forEach((id) => {
    const element = document.getElementById(id);
    element.classList.remove(gesture.className);
    void element.offsetWidth; // force reflow so a repeated gesture restarts
    element.classList.add(gesture.className);
  });
}

function doGesture(gestureName) {
  const gesture = GESTURES[gestureName];
  if (!gesture) {
    console.warn('Unknown gesture:', gestureName);
    return;
  }
  clearTimeout(gestureTimeoutIds[gestureName]);
  addGestureClass(gesture);
  gestureTimeoutIds[gestureName] = setTimeout(
    () => removeGestureClass(gesture),
    gesture.durationMs
  );
}


// ─── Speech bubbles ───────────────────────────────────────────
function showSpeechBubble(text) {
  const bubble = document.createElement('div');
  bubble.className = 'speech-bubble';
  bubble.textContent = text; // textContent keeps messages from becoming HTML
  bubble.style.transition = 'opacity ' + BUBBLE_FADE_MS + 'ms';
  document.getElementById('speech-bubbles').appendChild(bubble);

  setTimeout(() => {
    bubble.style.opacity = '0';
    setTimeout(() => bubble.remove(), BUBBLE_FADE_MS);
  }, SPEECH_BUBBLE_MS - BUBBLE_FADE_MS);
}
