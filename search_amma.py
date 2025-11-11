import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')

print("Searching for 'amma' and 'akka' in ALL columns...\n")

# Search for 'amma'
print("Where does 'amma' appear?")
amma_locations = []
for row_idx in range(1, len(df)):
    for col_idx in range(1, len(df.columns)):
        val = df.iloc[row_idx, col_idx]
        if pd.notna(val) and str(val).strip().lower() == 'amma':
            base_word = df.iloc[row_idx, 1]  # NP1 of this row
            amma_locations.append((row_idx, df.columns[col_idx], base_word))
            if len(amma_locations) <= 5:  # Show first 5
                print(f"  Row {row_idx}, Column '{df.columns[col_idx]}': base word is '{base_word}'")

print(f"\n  Total: Found 'amma' in {len(amma_locations)} locations")

# Search for 'akka'
print("\nWhere does 'akka' appear?")
akka_locations = []
for row_idx in range(1, len(df)):
    for col_idx in range(1, len(df.columns)):
        val = df.iloc[row_idx, col_idx]
        if pd.notna(val) and str(val).strip().lower() == 'akka':
            base_word = df.iloc[row_idx, 1]  # NP1 of this row
            akka_locations.append((row_idx, df.columns[col_idx], base_word))
            if len(akka_locations) <= 5:  # Show first 5
                print(f"  Row {row_idx}, Column '{df.columns[col_idx]}': base word is '{base_word}'")

print(f"\n  Total: Found 'akka' in {len(akka_locations)} locations")

# Search for 'ammanalli'
print("\nWhere does 'ammanalli' appear?")
ammanalli_locations = []
for row_idx in range(1, len(df)):
    for col_idx in range(1, len(df.columns)):
        val = df.iloc[row_idx, col_idx]
        if pd.notna(val) and 'ammanalli' in str(val).strip().lower():
            base_word = df.iloc[row_idx, 1]  # NP1 of this row
            ammanalli_locations.append((row_idx, df.columns[col_idx], val, base_word))
            print(f"  Row {row_idx}, Column '{df.columns[col_idx]}': '{val}' (base: '{base_word}')")

print(f"\n  Total: Found forms with 'ammanalli' in {len(ammanalli_locations)} locations")
