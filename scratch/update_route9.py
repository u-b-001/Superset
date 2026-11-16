with open("ai_integration/chart_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """computed_val, breakdown = dynamic_catalog.execute_slice_query(matched_slice)

                if computed_val is not None:

                    dyn_title = matched_slice["slice_name"]

                    dyn_category = matched_slice.get("dashboard_title", "Dynamic Dashboard")

                    dyn_target_kpi = f"slice_{matched_slice['slice_id']}"

                    dyn_filter_tag = matched_slice["slice_name"]

                    dyn_matched_slices = breakdown or {dyn_title: computed_val}

                    dyn_auth_text = f"According to verified records on the **{dyn_category}** dashboard, the current figure for **{dyn_title}** is **{computed_val:,}**." """

# Let's use simple find and replace for the exact line
old_line = "computed_val, breakdown = dynamic_catalog.execute_slice_query(matched_slice)"
new_line = "computed_val, resolved_tag, breakdown = dynamic_catalog.extract_metric_for_query(matched_slice, question)"
text = text.replace(old_line, new_line)

old_tag = 'dyn_filter_tag = matched_slice["slice_name"]'
new_tag = 'dyn_filter_tag = resolved_tag or matched_slice["slice_name"]'
text = text.replace(old_tag, new_tag)

old_auth = 'dyn_auth_text = f"According to verified records on the **{dyn_category}** dashboard, the current figure for **{dyn_title}** is **{computed_val:,}**."'
new_auth = 'dyn_auth_text = f"According to verified records on the **{dyn_category}** dashboard, the current figure for **{dyn_filter_tag}** is **{computed_val:,}** (matching the {dyn_title} chart)."'
text = text.replace(old_auth, new_auth)

with open("ai_integration/chart_engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("[OK] Updated Route 9 in chart_engine.py")

