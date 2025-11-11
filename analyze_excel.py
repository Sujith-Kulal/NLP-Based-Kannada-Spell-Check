import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')

print("=" * 70)
print("EXCEL FILE ANALYSIS")
print("=" * 70)

print(f"\n📊 Basic Info:")
print(f"  Total rows: {len(df):,}")
print(f"  Total columns: {len(df.columns)}")

# Count valid base words
valid_words = 0
for i in range(1, len(df)):  # Skip header row 0
    base_word = df.iloc[i, 1]
    if pd.notna(base_word) and str(base_word).strip() and str(base_word).strip().lower() != 'nan':
        valid_words += 1

print(f"  Valid base words: {valid_words:,}")

# Calculate total paradigm forms
print(f"\n📝 Paradigm Forms:")
print(f"  Columns per word: {len(df.columns) - 2} (excluding Sl No and base word)")
print(f"  Theoretical max forms: {valid_words:,} × {len(df.columns) - 2} = {valid_words * (len(df.columns) - 2):,}")

# Count actual non-empty forms
total_forms = 0
for i in range(1, min(100, len(df))):  # Sample first 100 rows
    for j in range(2, len(df.columns)):
        val = df.iloc[i, j]
        if pd.notna(val) and str(val).strip() and str(val).strip().lower() != 'nan':
            total_forms += 1

avg_forms_per_word = total_forms / min(99, len(df) - 1)
estimated_total = int(valid_words * avg_forms_per_word)

print(f"  Average forms per word (sample): {avg_forms_per_word:.1f}")
print(f"  Estimated total forms: {estimated_total:,}")

print(f"\n🔍 Why the mismatch?")
print(f"  Your calculation: 67,326 × 315 = 21,207,690")
print(f"  Actual base words: {valid_words:,}")
print(f"  Actual columns: {len(df.columns) - 2}")
print(f"  Estimated forms: {estimated_total:,}")

print(f"\n💡 Explanation:")
if valid_words < 67326:
    print(f"  - Base words is {valid_words:,}, not 67,326")
if len(df.columns) - 2 < 315:
    print(f"  - Paradigm columns is {len(df.columns) - 2}, not 315")
if avg_forms_per_word < len(df.columns) - 2:
    print(f"  - Not all paradigm slots are filled (avg {avg_forms_per_word:.1f} per word)")
