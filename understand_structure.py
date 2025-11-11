import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')

print("Understanding the REAL Excel structure...\n")
print("=" * 70)

# Row 0 is headers
print("Row 0 (Headers):")
for i, col in enumerate(df.columns[:15]):
    print(f"  Column {i}: {col}")

print("\nRow 1 (First data row - showing 'amma' example):")
row1 = df.iloc[1]
for i in range(min(15, len(row1))):
    val = row1.iloc[i]
    if pd.notna(val):
        print(f"  Column {i} ({df.columns[i]}): '{val}'")

print(f"\n💡 HYPOTHESIS:")
print(f"This looks like each ROW is one paradigm form,")
print(f"and each COLUMN shows that form for different base words!")
print(f"\nOR...")
print(f"Each ROW is a base word, and each COLUMN is a paradigm form?")

# Check row 1 column 9 specifically
val_np9 = df.iloc[1, 9]
print(f"\n🔍 Checking df.iloc[1, 9] (should be 'amma'): '{val_np9}'")

# Let me look at multiple rows to understand the pattern
print(f"\n📊 Pattern analysis - Column NP9 values (first 20 rows):")
for i in range(1, 21):
    val = df.iloc[i, 9]
    if pd.notna(val):
        print(f"  Row {i}: '{val}'")
