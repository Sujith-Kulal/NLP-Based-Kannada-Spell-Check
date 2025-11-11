from paradigm_generator import create_generator

print("Creating generator...")
g = create_generator()

print("\n🔍 Checking 'amma' paradigm forms:")
if 'amma' in g.all_paradigms:
    forms = g.all_paradigms['amma']
    print(f"Found {len(forms)} forms for 'amma':")
    for i, (key, val) in enumerate(list(forms.items())[:10]):
        print(f"   {key}: {val}")
    if len(forms) > 10:
        print(f"   ... and {len(forms) - 10} more")
else:
    print("'amma' not found in paradigms")

print("\n🔍 Checking 'akka' paradigm forms:")
if 'akka' in g.all_paradigms:
    forms = g.all_paradigms['akka']
    print(f"Found {len(forms)} forms for 'akka':")
    for i, (key, val) in enumerate(list(forms.items())[:10]):
        print(f"   {key}: {val}")
    if len(forms) > 10:
        print(f"   ... and {len(forms) - 10} more")
else:
    print("'akka' not found in paradigms")

print("\n🔍 Searching for words containing 'amman':")
matching = [w for w in g.all_inflected_forms if 'amman' in w][:20]
print(f"Found {len(matching)} words, showing first 20:")
for w in matching:
    print(f"   {w}")
