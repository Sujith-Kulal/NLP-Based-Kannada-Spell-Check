import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')

print(f"Excel file info:")
print(f"  Total rows: {len(df)}")
print(f"  Total columns: {len(df.columns)}")
print(f"\nColumn names (paradigm types):")
for i, col in enumerate(df.columns[:20]):
    print(f"  {i}: {col}")
print(f"  ... and {len(df.columns) - 20} more columns")

# Check if there's a locative case column (for -alli suffix)
locative_cols = [col for col in df.columns if 'alli' in str(col).lower() or 'loc' in str(col).lower()]
print(f"\n🔍 Columns that might contain locative (-alli) forms:")
for col in locative_cols[:10]:
    print(f"  {col}")

# Sample a word and show its paradigm
print(f"\n📝 Sample: paradigm for 'mara':")
mara_row = df[df.iloc[:, 1].str.lower() == 'mara']
if not mara_row.empty:
    row = mara_row.iloc[0]
    forms = [(col, val) for col, val in zip(df.columns[2:15], row.iloc[2:15]) if pd.notna(val)]
    for col, val in forms:
        print(f"  {col}: {val}")
