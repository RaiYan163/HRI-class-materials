#!/usr/bin/env node

/**
 * TOON Data Query Interface with Ollama
 * 
 * This script:
 * 1. Loads data from test.json
 * 2. Converts it to TOON format
 * 3. Sets up a prompt-engineered conversation system
 * 4. Allows querying the data through LLM conversations
 * 
 * Usage:
 *   node query-data.js "your question about the data"
 *   node query-data.js  (interactive mode)
 */

import { readFileSync } from 'fs';
import { encode } from '@toon-format/toon';
import ollama from 'ollama';

/**
 * Load and convert data from test.json to TOON format
 */
function loadDataAsToon() {
  console.log('Loading data from test.json...');
  const jsonData = readFileSync('test.json', 'utf-8');
  const data = JSON.parse(jsonData);
  
  // Convert to TOON format
  const toonData = encode(data, { delimiter: ',' });
  
  console.log(`✓ Loaded ${data.employees?.length || 0} employees\n`);
  return { data, toonData, jsonData };
}

/**
 * Create system prompt - following "show, don't describe" principle
 */
function createSystemPrompt(toonData) {
  return `You are a data analyst assistant.

Employee data (TOON format - 2-space indent, arrays show length and fields):

\`\`\`toon
${toonData}
\`\`\`

Answer questions about this data precisely.`;
}

/**
 * Query the LLM with a question about the data
 */
async function queryLLM(question, toonData, model = 'gemma3:4b') {
  const systemPrompt = createSystemPrompt(toonData);

  try {
    const response = await ollama.chat({
      model,
      messages: [
        {
          role: 'system',
          content: systemPrompt
        },
        {
          role: 'user',
          content: question
        }
      ]
    });

    return response.message.content;
  } catch (error) {
    throw new Error(`Failed to query LLM: ${error.message}`);
  }
}

/**
 * Check if Ollama is running
 */
async function checkOllama() {
  try {
    await ollama.list();
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Interactive mode - ask questions in a loop
 */
async function interactiveMode(toonData) {
  const readline = await import('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  console.log('\n' + '='.repeat(60));
  console.log('Interactive Data Query Mode');
  console.log('='.repeat(60));
  console.log('Ask questions about the employee data.');
  console.log('Type "exit" or "quit" to end.\n');

  const askQuestion = () => {
    rl.question('Your question: ', async (question) => {
      if (question.toLowerCase() === 'exit' || question.toLowerCase() === 'quit') {
        console.log('\nGoodbye!');
        rl.close();
        return;
      }

      if (question.trim() === '') {
        askQuestion();
        return;
      }

      console.log('\nThinking...\n');
      try {
        const answer = await queryLLM(question, toonData);
        console.log('Answer:', answer);
        console.log('\n' + '-'.repeat(60) + '\n');
      } catch (error) {
        console.error('Error:', error.message);
        console.log('\n' + '-'.repeat(60) + '\n');
      }

      askQuestion();
    });
  };

  askQuestion();
}

/**
 * Example queries to demonstrate the system
 */
async function runExampleQueries(toonData) {
  const examples = [
    'How many employees are in the Engineering department?',
    'What is the average salary across all employees?',
    'List all employees who were hired in 2020 or later.',
    'Which department has the most employees?',
    'Who are the highest paid employees?'
  ];

  console.log('\n' + '='.repeat(60));
  console.log('Running Example Queries');
  console.log('='.repeat(60) + '\n');

  for (let i = 0; i < examples.length; i++) {
    console.log(`Example ${i + 1}: ${examples[i]}`);
    console.log('-'.repeat(60));
    try {
      const answer = await queryLLM(examples[i], toonData);
      console.log(`Answer: ${answer}\n`);
    } catch (error) {
      console.error(`Error: ${error.message}\n`);
    }
    console.log();
  }
}

/**
 * Main execution
 */
async function main() {
  // Load data
  const { toonData } = loadDataAsToon();

  // Check Ollama
  const isRunning = await checkOllama();
  if (!isRunning) {
    console.log('Error: Ollama is not running!');
    console.log('Start Ollama with: ollama serve');
    process.exit(1);
  }

  // Get command line arguments
  const args = process.argv.slice(2);
  const question = args.join(' ');

  if (question) {
    // Single query mode
    console.log(`\nQuestion: ${question}\n`);
    console.log('='.repeat(60));
    try {
      const answer = await queryLLM(question, toonData);
      console.log('Answer:', answer);
    } catch (error) {
      console.error('Error:', error.message);
      process.exit(1);
    }
  } else {
    // Interactive mode
    await interactiveMode(toonData);
  }
}

// Run if executed directly
main().catch(error => {
  console.error('Fatal error:', error.message);
  process.exit(1);
});