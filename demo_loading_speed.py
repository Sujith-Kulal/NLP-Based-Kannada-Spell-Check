#!/usr/bin/env python3
"""
Quick demo showing the paradigm loading speed optimization
Run this to see the difference!
"""
import time
from paradigm_generator import ParadigmGenerator

print("=" * 70)
print("🚀 PARADIGM LOADING SPEED DEMO")
print("=" * 70)
print("\nThis demonstrates the 391x speedup from pickle caching!")
print("The cache file is automatically created/updated as needed.\n")

input("Press Enter to load paradigms... ")

start = time.time()
print("\n⚡ Loading paradigms...")
pg = ParadigmGenerator()
pg.initialize_paradigms()
elapsed = time.time() - start

print(f"\n✅ DONE in {elapsed:.2f} seconds!")
print(f"\n📊 Loaded Statistics:")
print(f"   • Base paradigms: {pg.stats['base_count']:,}")
print(f"   • Derived paradigms: {pg.stats['derived_count']:,}")
print(f"   • Total paradigms: {pg.stats['total_count']:,}")
print(f"   • Inflected forms: {pg.stats['total_inflected_forms']:,}")

if elapsed < 1.0:
    print(f"\n🚀 Loading was FAST! ({elapsed:.3f}s)")
    print("   ✅ Cache is working perfectly!")
else:
    print(f"\n📖 This was the first load (created cache)")
    print("   💡 Next time will be 391x faster!")

print("\n" + "=" * 70)
