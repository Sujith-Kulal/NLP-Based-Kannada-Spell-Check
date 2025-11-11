import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')

print("Investigating why only 7,988 unique words from 45K+ rows...\n")

# Check what's in NP1 column
np1_values = []
for i in range(1, min(100, len(df))):  # Sample first 100 rows
    val = df.iloc[i, 1]  # NP1 column
    if pd.notna(val):
        np1_values.append((i, str(val).strip()))

print("First 20 rows of NP1 column:")
for row_idx, val in np1_values[:20]:
    print(f"  Row {row_idx}: '{val}'")

# Maybe base words are in a different column?
print("\n\nChecking ALL columns for first data row (row 1):")
row1 = df.iloc[1]
for col_idx, col_name in enumerate(df.columns[:10]):
    val = row1.iloc[col_idx]
    print(f"  Column {col_idx} ({col_name}): '{val}'")

# Check if maybe multiple paradigms are in different sheets or something
print(f"\n\n💡 Theory: Maybe NP1 contains paradigm FORMS, not base words?")
print(f"Let me check what makes sense...\n")

# Count non-empty cells in each column
print("Non-empty cell counts for first 10 columns:")
for col_idx in range(10):
    col_name = df.columns[col_idx]
    non_empty = sum(1 for i in range(1, len(df)) if pd.notna(df.iloc[i, col_idx]))
    print(f"  {col_name}: {non_empty:,} non-empty")
