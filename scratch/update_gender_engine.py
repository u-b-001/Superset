import re

file_path = "ai_integration/chart_engine.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update DASHBOARD_STATS
old_stat = '''        "female": 15472,  # teaching slice (or 16,279 total workforce)

        "male": 5214,     # teaching slice (or 5,526 total workforce)

        "transgender": 19,

        "total": 20705,'''

new_stat = '''        "female": 16289,

        "male": 5543,

        "transgender": 19,

        "total": 21851,'''

if old_stat in content:
    content = content.replace(old_stat, new_stat)
    print("[OK] Replaced in DASHBOARD_STATS")
else:
    print("[WARN] old_stat not found in content, checking single-spaced")
    old_stat_single = '''        "female": 15472,  # teaching slice (or 16,279 total workforce)\n        "male": 5214,     # teaching slice (or 5,526 total workforce)\n        "transgender": 19,\n        "total": 20705,'''
    new_stat_single = '''        "female": 16289,\n        "male": 5543,\n        "transgender": 19,\n        "total": 21851,'''
    if old_stat_single in content:
        content = content.replace(old_stat_single, new_stat_single)
        print("[OK] Replaced single-spaced in DASHBOARD_STATS")

# 2. Update Route 5 female
old_female_route = '''        val = 15472

        auth_text = "According to verified department records, there are **15,472** female teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart)."

        matched_slices = {"Female": 15472, "FEMALE": 15472}'''

new_female_route = '''        val = 16289

        auth_text = "According to verified department records, there are **16,289** female teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart: 16.3k, 74.55%)."

        matched_slices = {"Female": 16289, "FEMALE": 16289}'''

if old_female_route in content:
    content = content.replace(old_female_route, new_female_route)
    print("[OK] Replaced female route")
else:
    print("[WARN] old_female_route not found, trying regex")
    content = re.sub(
        r'val\s*=\s*15472\s*\n+.*?auth_text\s*=\s*".*?15,472.*?"\s*\n+.*?matched_slices\s*=\s*\{"Female":\s*15472,\s*"FEMALE":\s*15472\}',
        'val = 16289\n\n        auth_text = "According to verified department records, there are **16,289** female teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart: 16.3k, 74.55%)."\n\n        matched_slices = {"Female": 16289, "FEMALE": 16289}',
        content,
        flags=re.DOTALL
    )
    print("[OK] Regex replaced female route")

# 3. Update Route 5 male
old_male_route = '''        val = 5214

        auth_text = "According to verified department records, there are **5,214** male teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart)."

        matched_slices = {"Male": 5214, "MALE": 5214}'''

new_male_route = '''        val = 5543

        auth_text = "According to verified department records, there are **5,543** male teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart: 5.5k, 25.37%)."

        matched_slices = {"Male": 5543, "MALE": 5543}'''

if old_male_route in content:
    content = content.replace(old_male_route, new_male_route)
    print("[OK] Replaced male route")
else:
    print("[WARN] old_male_route not found, trying regex")
    content = re.sub(
        r'val\s*=\s*5214\s*\n+.*?auth_text\s*=\s*".*?5,214.*?"\s*\n+.*?matched_slices\s*=\s*\{"Male":\s*5214,\s*"MALE":\s*5214\}',
        'val = 5543\n\n        auth_text = "According to verified department records, there are **5,543** male teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart: 5.5k, 25.37%)."\n\n        matched_slices = {"Male": 5543, "MALE": 5543}',
        content,
        flags=re.DOTALL
    )
    print("[OK] Regex replaced male route")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("[OK] Written updated content to", file_path)

