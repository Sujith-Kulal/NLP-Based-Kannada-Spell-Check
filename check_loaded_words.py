from paradigm_generator import create_generator

g = create_generator()
words = list(g.all_paradigms.keys())[:20]
print('\nFirst 20 base words loaded:')
for w in words:
    print(f'  - {w}')
    
print(f'\nTotal words with paradigms: {len(g.all_paradigms)}')
