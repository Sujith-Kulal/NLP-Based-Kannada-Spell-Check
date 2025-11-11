import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')

# Get all base words (column index 1, skip row 0)
all_base_words = []
for i in range(1, len(df)):
    base = df.iloc[i, 1]
    if pd.notna(base):
        base_str = str(base).strip().lower()
        if base_str and base_str != 'nan':
            all_base_words.append(base_str)

print(f"Total rows with base words: {len(all_base_words):,}")
print(f"Unique base words: {len(set(all_base_words)):,}")

# Check duplicates
from collections import Counter
counts = Counter(all_base_words)
duplicates = {word: count for word, count in counts.items() if count > 1}

print(f"\nWords appearing multiple times: {len(duplicates):,}")
print(f"\nTop 10 most repeated words:")
for word, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {word}: {count} times")

# Check if amma exists anywhere
if 'amma' in all_base_words:
    print(f"\n✅ 'amma' found in Excel!")
    print(f"   Appears {counts['amma']} time(s)")
else:
    print(f"\n❌ 'amma' NOT in Excel")
    print(f"   Looking for similar...")
    similar = [w for w in set(all_base_words) if 'amma' in w][:10]
    for w in similar:
        print(f"   - {w}")
