#!/usr/bin/env python
# -*- coding: utf-8 -*-

from kannada_wx_converter import kannada_to_wx, wx_to_kannada, is_kannada_text

print("=" * 70)
print("Testing WX ↔ Kannada Conversion")
print("=" * 70)

# Test 1: Kannada → WX → Kannada (Round-trip)
print("\n1. Round-trip Test:")
print("-" * 70)
test_words = ["ಇವರಲಿ", "ಬರಲಿ", "ಅವರಲ್ಲಿ", "ಮರ", "ಹುಡುಗ"]

for word in test_words:
    wx = kannada_to_wx(word)
    back = wx_to_kannada(wx)
    match = "✅" if word == back else "❌"
    print(f"{match} {word:15} → {wx:15} → {back:15}")

# Test 2: WX → Kannada (Suggestions)
print("\n2. Convert WX Suggestions to Kannada:")
print("-" * 70)
wx_suggestions = ['barali', 'irali', 'ivara', 'ivaraxu', 'varaxi', 'avaralli']

for wx in wx_suggestions:
    kannada = wx_to_kannada(wx)
    print(f"  {wx:15} → {kannada:15}")

# Test 3: Check if conversion is correct
print("\n3. Specific Test for ivarali:")
print("-" * 70)
original = "ಇವರಲಿ"
print(f"Original Kannada:  {original}")

wx = kannada_to_wx(original)
print(f"Converted to WX:   {wx}")

# Simulate spell checker suggestion
suggestion_wx = "barali"
print(f"Suggestion (WX):   {suggestion_wx}")

# Convert suggestion back to Kannada
suggestion_kannada = wx_to_kannada(suggestion_wx)
print(f"Suggestion (Kannada): {suggestion_kannada}")

print("\n" + "=" * 70)
print(f"Expected result: ಬರಲಿ")
print(f"Actual result:   {suggestion_kannada}")
print(f"Match: {'✅' if suggestion_kannada == 'ಬರಲಿ' else '❌'}")
print("=" * 70)
