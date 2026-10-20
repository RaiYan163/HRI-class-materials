// convert.js - Simple JSON to TOON converter

import { readFileSync, writeFileSync } from 'fs';

import { encode } from '@toon-format/toon';

console.log('Converting JSON to TOON...\n');

// Step 1: Read the JSON file

console.log('Reading test.json...');

const jsonData = readFileSync('test.json', 'utf-8');

const data = JSON.parse(jsonData);

console.log(`Loaded successfully!\n`);

// Step 2: Convert to TOON

console.log('Converting to TOON format...');

const toonData = encode(data);

console.log('Conversion complete!\n');

// Step 3: Save to file

console.log('Saving to output.toon...');

writeFileSync('output.toon', toonData, 'utf-8');

console.log('Saved successfully!\n');

// Step 4: Show comparison

console.log('=' .repeat(60));

console.log('COMPARISON:');

console.log('=' .repeat(60));

console.log(`JSON size:  ${jsonData.length} characters`);

console.log(`TOON size:  ${toonData.length} characters`);

console.log(`Savings:    ${jsonData.length - toonData.length} characters (${((jsonData.length - toonData.length) / jsonData.length * 100).toFixed(1)}%)`);

console.log('=' .repeat(60));

console.log();

// Step 5: Show preview

console.log('TOON OUTPUT PREVIEW:');

console.log('-' .repeat(60));

console.log(toonData);

console.log('-' .repeat(60));

console.log();

console.log('Done! Check output.toon for the full result.');

