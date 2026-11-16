import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_integration.dynamic_catalog import dynamic_catalog
import re

dynamic_catalog.refresh()
q = 'how many government schoolds are there?'
q_clean = q.lower().strip()

s_info = dynamic_catalog.slices[6]
print("Slice 6 groupby:", s_info.get("groupby"))
for gb_item in s_info.get("groupby") or []:
    if isinstance(gb_item, dict):
        gb_name = (gb_item.get("label") or gb_item.get("sqlExpression") or "").lower()
    else:
        gb_name = str(gb_item).lower()
    print("gb_name:", gb_name)
    if "gender" in gb_name and any(g in q_clean for g in ["female", "male", "women", "men", "transgender"]):
        print("MATCHED GENDER!")
