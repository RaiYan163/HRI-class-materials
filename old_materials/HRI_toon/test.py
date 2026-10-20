#!/usr/bin/env python3

"""

Simple TOON Demo - Reading JSON and Converting to TOON

"""

import json

from toon_format import encode

# Step 1: Read the JSON file

print("=" * 80)

print("TOON Format Demo - JSON to TOON Conversion")

print("=" * 80)

print()

print("Step 1: Reading JSON file...")

with open('test.json', 'r') as f:

    data = json.load(f)

print(f"Loaded {len(data['employees'])} employees")

print()

# Step 2: Show original JSON (formatted)

print("ORIGINAL JSON FORMAT:")

print("-" * 80)

json_string = json.dumps(data, indent=2)

print(json_string)

print()

print(f"Character count: {len(json_string)}")

print()

print()

# Step 3: Convert to TOON

print("CONVERTED TO TOON FORMAT:")

print("-" * 80)

toon_string = encode(data)

print(toon_string)

print()

print(f"Character count: {len(toon_string)}")

print()

print()

# Step 4: Save TOON format to text file

print("Saving TOON format to file...")

with open('test_toon.txt', 'w') as f:

    f.write(toon_string)

print("TOON format saved to 'test_toon.txt'")

print()

# Step 5: Show comparison

print("EFFICIENCY COMPARISON:")

print("-" * 80)

savings = len(json_string) - len(toon_string)

savings_percent = (savings / len(json_string) * 100)

print(f"JSON:  {len(json_string):,} characters")

print(f"TOON:  {len(toon_string):,} characters")

print(f"Saved: {savings:,} characters ({savings_percent:.1f}% reduction!)")

print()

# Step 6: Token estimation

print("ESTIMATED TOKEN USAGE:")

print("-" * 80)

# Rough estimate: 1 token ≈ 4 characters

json_tokens = len(json_string) // 4

toon_tokens = len(toon_string) // 4

token_savings = json_tokens - toon_tokens

print(f"JSON:  ~{json_tokens:,} tokens")

print(f"TOON:  ~{toon_tokens:,} tokens")

print(f"Saved: ~{token_savings:,} tokens")

print()

# Step 7: Cost estimation

print("ESTIMATED COST (at $0.003/1K tokens):")

print("-" * 80)

json_cost = (json_tokens / 1000) * 0.003

toon_cost = (toon_tokens / 1000) * 0.003

cost_savings = json_cost - toon_cost

print(f"JSON:  ${json_cost:.6f} per API call")

print(f"TOON:  ${toon_cost:.6f} per API call")

print(f"Saved: ${cost_savings:.6f} per API call")

print()

# Step 8: Scaled up example

print("SCALED UP (1000 API calls/day):")

print("-" * 80)

daily_savings = cost_savings * 1000

monthly_savings = daily_savings * 30

print(f"Daily savings:   ${daily_savings:.2f}")

print(f"Monthly savings: ${monthly_savings:.2f}")

print(f"Yearly savings:  ${monthly_savings * 12:.2f}")

print()

print("=" * 80)

print("KEY TAKEAWAY:")

print("TOON writes field names ONCE, JSON repeats them for EVERY record.")

print("More fields + more records = bigger savings!")

print("=" * 80)

