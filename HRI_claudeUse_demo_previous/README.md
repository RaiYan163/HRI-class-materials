# Project Coding Guidelines

> **For students:** Read this before you start coding.  
> **For Claude Code:** Always follow these guidelines when writing any code for this project.

---

## Who This Is For

This README was written by your teacher. It applies to **every file** you create in this project — HTML, CSS, JavaScript, or any other language. These are not optional. Whether you are writing code yourself or using Claude Code to help you, the output must follow these standards.

When using Claude Code, paste this file as context at the start of your session. Claude Code will read and apply these guidelines automatically.

---

## 1. File and Folder Structure

Keep your project organized from day one. A messy folder makes it hard to find files and hard to collaborate.

**Rules:**
- One folder per project. All project files go inside it. Nothing on the Desktop.
- Use lowercase filenames only. No spaces — use hyphens instead.
  - Good: `login-page.html`, `main-styles.css`, `app.js`
  - Bad: `Login Page.html`, `MainStyles.CSS`, `APP.js`
- Separate your files by type if the project grows:
  ```
  my-project/
  ├── index.html
  ├── css/
  │   └── styles.css
  ├── js/
  │   └── main.js
  └── README.md
  ```
- Never dump everything in one file if it gets longer than ~150 lines. Split it up.

---

## 2. Naming Things

Names should tell you **what something is or does** without needing a comment to explain it.

### Variables
- Use `camelCase` for variable and function names.
- Use descriptive names. A name like `x` or `data` or `temp` tells nobody anything.

```js
// Bad
let x = document.getElementById('msg');
let d = 'hello';

// Good
let messageInput = document.getElementById('message-input');
let greetingText = 'hello';
```

### Functions
- Function names should start with a **verb** — they do something.
- The name should describe exactly what the function does.

```js
// Bad
function thing() { ... }
function stuff() { ... }

// Good
function submitForm(data) { ... }
function fetchUserProfile(userId) { ... }
function showErrorMessage(text) { ... }
```

### Constants
- If a value never changes, use `const` and write the name in `UPPER_SNAKE_CASE`.

```js
const MAX_USERNAME_LENGTH = 30;
const TIMEOUT_MS = 5000;
const API_BASE_URL = 'https://api.example.com';
```

### HTML IDs and Classes
- Use lowercase with hyphens (called kebab-case).
- IDs should be unique on a page. Classes are for reusable styles.

```html
<!-- Bad -->
<div id="UserCard" class="CardItem"></div>

<!-- Good -->
<div id="user-card" class="card-item"></div>
```

---

## 3. Comments

Comments explain **why** something is done, not **what** — the code itself should show what. Write a comment when:
- The logic is not immediately obvious
- You are making a deliberate choice that might look odd
- You are marking a section to make the file easier to scan

### Section headers
Use comments to divide long files into clear sections.

```js
// ─── Constants ────────────────────────────────────────────────
const TIMEOUT_MS = 5000;

// ─── Data fetching ────────────────────────────────────────────
function fetchUserData(userId) { ... }

// ─── UI updates ───────────────────────────────────────────────
function renderUserCard(user) { ... }
```

### Inline comments
Keep them short and on the same line, or just above the line they refer to.

```js
const TIMEOUT_MS = 5000; // wait 5s before showing a timeout error

// Clear the form after successful submission
resetForm();
```

### What NOT to comment
Do not comment obvious things. It clutters the code and adds noise.

```js
// Bad — the code already says this
let count = 0; // set count to zero

// Good — explains why, not what
let count = 0; // start from zero so the first ID assigned is 1
```

---

## 4. Code Formatting

Consistent formatting makes code easy to read for you, your teacher, and your teammates.

### Indentation
- Use **2 spaces** for indentation (not tabs, not 4 spaces — 2 spaces).
- Every nested block gets one more level of indentation.

```js
// Good
function saveUserData(user) {
  if (user.name.length === 0) {
    console.log('Empty name, skipping');
    return;
  }
  updateDatabase(user);
}
```

### Line length
- Keep lines under **80 characters** wide.
- If a line is too long, break it up.

```js
// Bad — too long
fetch('/api/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(userData) });

// Good
const options = {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(userData)
};
fetch('/api/save', options);
```

### Blank lines
- One blank line between functions.
- Two blank lines between major sections.
- No trailing blank lines at the end of a file.

### Quotes
- Pick **single quotes** `'` for JavaScript strings and stick with them throughout the file.
- Only use double quotes `"` when the string itself contains a single quote.

```js
// Good
const greeting = 'Hello, world!';
const message = "It's working!"; // single quote inside, so use double
```

---

## 5. Functions — Keep Them Small

A function should do **one thing only**. If you need to describe what a function does and you use the word "and", it probably does too much.

```js
// Bad — this function does too many things
function handleSubmit() {
  let name = document.getElementById('name-input').value;
  document.getElementById('name-input').value = '';
  document.getElementById('results').innerHTML += '<p>' + name + '</p>';
  fetch('/api/save', { method: 'POST', body: JSON.stringify({ name }) });
}

// Good — each function has one job
function getNameInput() {
  return document.getElementById('name-input').value;
}

function clearNameInput() {
  document.getElementById('name-input').value = '';
}

function appendToResults(text) {
  const results = document.getElementById('results');
  const entry = document.createElement('p');
  entry.textContent = text;
  results.appendChild(entry);
}

function saveToServer(name) {
  fetch('/api/save', { method: 'POST', body: JSON.stringify({ name }) });
}
```

---

## 6. Avoid Magic Numbers

A "magic number" is a raw number in your code with no explanation. Always give numbers a name.

```js
// Bad — what does 5000 mean? What about 3?
setTimeout(() => hideNotification(), 5000);
if (password.length < 3) return false;

// Good
const NOTIFICATION_DURATION_MS = 5000;
const MIN_PASSWORD_LENGTH = 3;

setTimeout(() => hideNotification(), NOTIFICATION_DURATION_MS);
if (password.length < MIN_PASSWORD_LENGTH) return false;
```

---

## 7. Error Handling

Always expect things to go wrong. Handle errors gracefully instead of letting the program crash silently.

```js
// Bad — if the request fails, nothing happens
fetch('/api/data');

// Good — handle success and failure
fetch('/api/data')
  .then(response => {
    if (!response.ok) {
      throw new Error('Server returned ' + response.status);
    }
    return response.json();
  })
  .then(data => {
    renderData(data);
  })
  .catch(error => {
    console.error('Failed to load data:', error);
    showErrorMessage('Could not load data. Please try again.');
  });
```

For data you receive externally, always validate before using:

```js
function handleIncomingData(raw) {
  try {
    const data = JSON.parse(raw);
    if (!data.type) {
      console.warn('Received data with no type field:', data);
      return;
    }
    processData(data);
  } catch (err) {
    console.error('Failed to parse data:', err);
  }
}
```

---

## 8. HTML Best Practices

### Structure
- Always include a proper `<!DOCTYPE html>`, `<html>`, `<head>`, and `<body>`.
- Always set the `lang` attribute on `<html>`.
- Always include a `<meta charset="UTF-8">` and a `<title>`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Project</title>
  <link rel="stylesheet" href="css/styles.css">
</head>
<body>
  <!-- content here -->
  <script src="js/main.js"></script>
</body>
</html>
```

### Separation of concerns
- **HTML** = structure (what is on the page)
- **CSS** = appearance (what it looks like)
- **JavaScript** = behaviour (what it does)

Do not mix them:

```html
<!-- Bad — style and behaviour mixed into HTML -->
<button style="background: purple; color: white;" onclick="submitForm()">Submit</button>

<!-- Good — each concern in its own place -->
<button class="submit-btn" id="btn-submit">Submit</button>
```

```css
/* styles.css */
.submit-btn {
  background: purple;
  color: white;
}
```

```js
// main.js
document.getElementById('btn-submit').addEventListener('click', () => {
  submitForm();
});
```

---

## 9. `var` Is Banned — Use `let` and `const`

Never use `var`. It has unpredictable behaviour due to how JavaScript scoping works. Use:
- `const` when the value will never be reassigned
- `let` when the value will change

```js
// Banned
var userName = 'Alice';
var itemCount = 0;

// Good
const DEFAULT_USER = 'Alice'; // never changes
let itemCount = 0;             // will change as items are added
```

---

## 10. Git Commit Messages (if using Git)

Write commit messages that describe **what changed and why**, not just "update" or "fix".

```
# Bad
git commit -m "update"
git commit -m "fix stuff"
git commit -m "asdfgh"

# Good
git commit -m "Add login form with validation"
git commit -m "Fix button not responding on mobile screens"
git commit -m "Add error message when API request fails"
```

Use the format: **verb + what + why (if not obvious)**

---

## Quick Reference Card

| Rule | Short version |
|---|---|
| File names | lowercase, hyphens, no spaces |
| Variables / functions | camelCase, descriptive |
| Constants | UPPER_SNAKE_CASE |
| HTML IDs / classes | kebab-case |
| Indentation | 2 spaces |
| Line length | max 80 characters |
| Quotes (JS) | single quotes |
| `var` | never — use `const` or `let` |
| Functions | one job each |
| Magic numbers | always give them a name |
| Comments | explain why, not what |
| Errors | always handle them |

---

## A Note on Using Claude Code

Claude Code will read this README and apply these guidelines when generating code for your project. However, you are still responsible for reviewing what it produces. When Claude Code writes code:

1. Read through it — do not just copy and run it blindly
2. Check that names are descriptive and make sense to you
3. Check that functions are small and focused
4. Ask Claude Code to explain anything you do not understand
5. If something does not follow these guidelines, tell Claude Code to fix it

Learning to read and critique code is just as important as learning to write it.

---

*Guidelines written by your teacher. When in doubt, ask.*
