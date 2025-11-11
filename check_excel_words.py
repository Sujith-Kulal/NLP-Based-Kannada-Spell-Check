import pandas as pd

df = pd.read_excel('check_pos/all.xlsx')
words = [str(row).strip().lower() for row in df.iloc[1:, 1] if pd.notna(row) and str(row).strip() != 'nan']

am_words = [w for w in words if w.startswith('am')][:30]
ak_words = [w for w in words if w.startswith('ak')][:30]

print(f'Total base words in Excel: {len(words)}')
print(f'\nWords starting with "am": ({len([w for w in words if w.startswith("am")])} total)')
for w in am_words:
    print(f'  {w}')

print(f'\nWords starting with "ak": ({len([w for w in words if w.startswith("ak")])} total)')
for w in ak_words:
    print(f'  {w}')

# Check specifically
print(f'\n🔍 Specific checks:')
for test in ['amma', 'akka', 'mara']:
    found = test in words
    print(f'  {test}: {"✅ Found" if found else "❌ Not found"}')
