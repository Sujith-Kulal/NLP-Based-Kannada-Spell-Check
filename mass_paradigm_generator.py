import os
import pandas as pd
import pickle
from glob import glob
from tqdm import tqdm

# Import your main spell checker
from enhanced_spell_checker import SimplifiedSpellChecker


def mass_generate_paradigms(paradigm_dir="paradigms/all", excel_path="all.xlsx", output_cache="auto_paradigm_cache.pkl"):
    """
    Generate full paradigms for all variant words from all base paradigm files.
    If 65 base paradigm files and 74,305 variant roots exist,
    this will produce about 4.8 million paradigm forms and store them in one cache file.
    """
    checker = SimplifiedSpellChecker(use_paradigm_generator=False)
    generated_paradigms = {}

    # --- Step 1: Load all base paradigm rules ---
    base_paradigm_files = glob(os.path.join(paradigm_dir, "*.txt"))
    base_rules = {}
    for file_path in base_paradigm_files:
        base = os.path.basename(file_path).split("_")[0]
        rules = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    rules.append(parts[1])
        base_rules[base] = rules

    print(f"✅ Loaded {len(base_rules)} base paradigm files")

    # --- Step 2: Load all variant words from Excel (with caching) ---
    excel_cache = excel_path.replace('.xlsx', '_variants.pkl')
    
    # Try loading from cache first
    if os.path.exists(excel_cache) and os.path.getmtime(excel_cache) >= os.path.getmtime(excel_path):
        print(f"⚡ Loading variants from cache: {excel_cache}")
        with open(excel_cache, 'rb') as f:
            variants = pickle.load(f)
    else:
        print(f"📖 Loading variants from Excel (first time, slow): {excel_path}")
        df = pd.read_excel(excel_path, header=None)
        variants = set()
        for _, row in df.iterrows():
            for cell in row:
                word = str(cell).strip()
                if word:
                    variants.add(word)
        variants = sorted(variants)
        
        # Save cache for next time
        with open(excel_cache, 'wb') as f:
            pickle.dump(variants, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"💾 Saved variants cache to: {excel_cache}")
    
    print(f"✅ Loaded {len(variants):,} variant roots from Excel")

    # --- Step 3: Generate paradigms ---
    total_generated = 0
    for variant_root in tqdm(variants, desc="Generating paradigms"):
        generated_paradigms[variant_root] = []
        for base_root, rules in base_rules.items():
            for rule in rules:
                try:
                    surface = checker._apply_paradigm_rule(base_root, variant_root, rule)
                    if surface:
                        generated_paradigms[variant_root].append(surface)
                        total_generated += 1
                except Exception:
                    continue

    print(f"\n✅ Generated total {total_generated:,} paradigm forms across {len(variants):,} variants")

    # --- Step 4: Save to cache ---
    with open(output_cache, "wb") as f:
        pickle.dump(generated_paradigms, f)

    print(f"✅ Cache saved to {output_cache}")


if __name__ == "__main__":
    mass_generate_paradigms()
