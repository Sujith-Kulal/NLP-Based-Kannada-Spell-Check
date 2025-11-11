from paradigm_generator import create_generator

print("Creating generator...")
g = create_generator()

print(f"\n✅ RESULTS:")
print(f"   Base words: {g.stats['base_count']:,}")
print(f"   Derived words: {g.stats['derived_count']:,}")
print(f"   Total paradigms: {g.stats['total_count']:,}")
print(f"   Total inflected forms: {g.stats['total_inflected_forms']:,}")

print(f"\n🔍 Checking specific words:")
test_words = ['amma', 'ammanalli', 'akka', 'akkanalli', 'mara', 'maravu']
for w in test_words:
    found = w in g.all_inflected_forms
    print(f"   {w}: {'✅ Found' if found else '❌ Not found'}")
