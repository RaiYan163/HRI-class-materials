#!/usr/bin/env node

/**
 * TOON Format Integration with Ollama
 * 
 * This script demonstrates how to:
 * 1. Encode data to TOON format using the npm library
 * 2. Send TOON-formatted data as input to Ollama models
 * 3. Request TOON-formatted output from Ollama models
 * 4. Validate the generated TOON output using strict mode
 * 
 * Prerequisites:
 * - Ollama installed and running on Mac
 * - Node.js with npm
 * - Install dependencies: npm install @toon-format/toon
 */

import { encode, decode } from '@toon-format/toon';

const OLLAMA_API = 'http://localhost:11434/api/generate';

/**
 * Example 1: Encode data to TOON and send as input to Ollama
 * Demonstrates the "show, don't describe" principle
 */
async function sendToonInputPrompt(model = 'llama3.2') {
  // Sample data to encode
  const users = [
    { id: 1, name: 'Alice', role: 'admin', lastLogin: '2025-01-15T10:30:00Z' },
    { id: 2, name: 'Bob', role: 'user', lastLogin: '2025-01-14T15:22:00Z' },
    { id: 3, name: 'Charlie', role: 'user', lastLogin: '2025-01-13T09:45:00Z' }
  ];

  // Encode to TOON format using the library
  const toonData = encode({ users });

  // Construct prompt following the documentation pattern
  const prompt = `Data is in TOON format (2-space indent, arrays show length and fields).

\`\`\`toon
${toonData}
\`\`\`

Task: Summarize the user roles and their last activity.`;

  console.log('='.repeat(60));
  console.log('Example 1: Sending TOON as Input');
  console.log('='.repeat(60));
  console.log(`Encoded TOON data:\n${toonData}\n`);
  console.log(`Prompt:\n${prompt}\n`);

  // Send to Ollama
  const response = await fetch(OLLAMA_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      prompt,
      stream: false
    })
  });

  const result = await response.json();
  console.log(`Response:\n${result.response}\n`);
}

/**
 * Example 2: Request model to generate TOON output
 * Be explicit about format and rules
 */
async function requestToonOutput(model = 'llama3.2') {
  // Encode input data
  const users = [
    { id: 1, name: 'Alice', role: 'admin', lastLogin: '2025-01-15T10:30:00Z' },
    { id: 2, name: 'Bob', role: 'user', lastLogin: '2025-01-14T15:22:00Z' },
    { id: 3, name: 'Charlie', role: 'user', lastLogin: '2025-01-13T09:45:00Z' }
  ];

  const toonData = encode({ users });

  // Explicit prompt for TOON generation
  const prompt = `Data is in TOON format (2-space indent, arrays show length and fields).

\`\`\`toon
${toonData}
\`\`\`

Task: Return only users with role "user" as TOON. Use the same header format. Set [N] to match the row count. Output only the code block.

Rules for TOON output:
- 2-space indent
- No trailing spaces
- [N] must match actual row count
- Format: arrayname[N]{field,names}:`;

  console.log('='.repeat(60));
  console.log('Example 2: Requesting TOON Output');
  console.log('='.repeat(60));
  console.log(`Prompt:\n${prompt}\n`);

  const response = await fetch(OLLAMA_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      prompt,
      stream: false
    })
  });

  const result = await response.json();
  console.log(`Response:\n${result.response}\n`);
  return result.response;
}

/**
 * Example 3: Use tab-separated format for better token efficiency
 */
async function requestToonWithTabs(model = 'llama3.2') {
  // Encode with tab delimiter
  const events = [
    { id: 1, level: 'error', message: 'Connection timeout', timestamp: '2025-01-15T10:00:00Z' },
    { id: 2, level: 'warn', message: 'Slow query', timestamp: '2025-01-15T10:05:00Z' },
    { id: 3, level: 'info', message: 'User login', timestamp: '2025-01-15T10:10:00Z' },
    { id: 4, level: 'error', message: 'Database error', timestamp: '2025-01-15T10:15:00Z' }
  ];

  // Use tab delimiter for maximum token efficiency
  const toonData = encode({ events }, { delimiter: '\t' });

  const prompt = `System logs in TOON format (tab-separated):

\`\`\`toon
${toonData}
\`\`\`

Task: Return only error-level events as TOON. Use the same format with tab-separated fields.

Rules:
- Fields are tab-separated (not comma-separated)
- 2-space indent
- [N] must match row count
- Output only the code block`;

  console.log('='.repeat(60));
  console.log('Example 3: Tab-Separated TOON (Most Token-Efficient)');
  console.log('='.repeat(60));
  console.log(`Encoded TOON data:\n${toonData}\n`);
  console.log(`Prompt:\n${prompt}\n`);

  const response = await fetch(OLLAMA_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      prompt,
      stream: false
    })
  });

  const result = await response.json();
  console.log(`Response:\n${result.response}\n`);
  return result.response;
}

/**
 * Example 4: Validate TOON output using strict mode
 * This is the recommended approach from the documentation
 */
function validateToonOutput(toonString) {
  console.log('='.repeat(60));
  console.log('Example 4: TOON Validation with Strict Mode');
  console.log('='.repeat(60));
  console.log(`Input to validate:\n${toonString}\n`);

  try {
    // Decode with strict mode (default) to catch errors
    const data = decode(toonString, { strict: true });
    
    console.log('✓ Validation Passed!');
    console.log('✓ Count matches [N]');
    console.log('✓ Indentation correct');
    console.log('✓ Escaping valid');
    console.log(`\nDecoded data:`, JSON.stringify(data, null, 2));
    
    return data;
  } catch (error) {
    console.log('❌ Validation Failed!');
    console.log(`Error: ${error.message}`);
    console.log('\nPossible issues:');
    console.log('- Count mismatch (row count ≠ [N])');
    console.log('- Invalid indentation');
    console.log('- Malformed escaping');
    console.log('- Truncated output');
    
    return null;
  }
}

/**
 * Example 5: Complete workflow - encode, send, receive, validate
 */
async function completeWorkflow(model = 'llama3.2') {
  console.log('='.repeat(60));
  console.log('Example 5: Complete Workflow');
  console.log('='.repeat(60));

  // Step 1: Encode input data
  const events = [
    { id: 1, level: 'error', message: 'Connection timeout', timestamp: '2025-01-15T10:00:00Z' },
    { id: 2, level: 'warn', message: 'Slow query', timestamp: '2025-01-15T10:05:00Z' },
    { id: 3, level: 'info', message: 'User login', timestamp: '2025-01-15T10:10:00Z' },
    { id: 4, level: 'error', message: 'Database error', timestamp: '2025-01-15T10:15:00Z' }
  ];

  const toonInput = encode({ events }, { delimiter: '\t' });
  console.log('Step 1: Encoded input data');

  // Step 2: Send to model
  const prompt = `System logs in TOON format (tab-separated):

\`\`\`toon
${toonInput}
\`\`\`

Task: Return only error-level events as TOON. Use the same format.`;

  console.log('Step 2: Sending to Ollama...');

  const response = await fetch(OLLAMA_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      prompt,
      stream: false
    })
  });

  const result = await response.json();
  const modelOutput = result.response;
  
  console.log(`Step 3: Received response:\n${modelOutput}\n`);

  // Step 4: Validate with strict mode
  console.log('Step 4: Validating output with strict mode...');
  
  // Extract TOON from code block if present
  let toonOutput = modelOutput;
  const codeBlockMatch = modelOutput.match(/```(?:toon)?\n([\s\S]+?)\n```/);
  if (codeBlockMatch) {
    toonOutput = codeBlockMatch[1];
  }

  const validated = validateToonOutput(toonOutput);
  
  if (validated) {
    console.log('\n✓ Complete workflow succeeded!');
  } else {
    console.log('\n❌ Validation failed - model output was malformed');
  }
}

/**
 * Check if Ollama is running
 */
async function checkOllama() {
  try {
    const response = await fetch('http://localhost:11434');
    return response.ok;
  } catch (error) {
    return false;
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('\n🚀 TOON + Ollama Integration Examples\n');

  // Check if Ollama is running
  const isRunning = await checkOllama();
  if (!isRunning) {
    console.log('❌ Error: Ollama is not running!');
    console.log('Start Ollama with: ollama serve');
    process.exit(1);
  }

  try {
    // Example 1: Send TOON as input
    await sendToonInputPrompt();

    // Example 2: Request TOON output
    await requestToonOutput();

    // Example 3: Tab-separated TOON
    await requestToonWithTabs();

    // Example 4: Validate TOON output
    const sampleOutput = `users[2]{id,name,role,lastLogin}:
  2,Bob,user,2025-01-14T15:22:00Z
  3,Charlie,user,2025-01-13T09:45:00Z`;
    
    validateToonOutput(sampleOutput);

    // Example 5: Complete workflow
    await completeWorkflow();

    console.log('\n' + '='.repeat(60));
    console.log('Integration complete!');
    console.log('='.repeat(60));
    console.log('\nKey takeaways:');
    console.log('1. Use encode() to create TOON from data');
    console.log('2. Show TOON examples in prompts, don\'t describe');
    console.log('3. Be explicit when requesting TOON output');
    console.log('4. Always validate with decode(output, {strict: true})');
    console.log('5. Use delimiter: \'\\t\' for better token efficiency');
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Run if executed directly
main();


