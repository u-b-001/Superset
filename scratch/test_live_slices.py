import sys
sys.path.insert(0, '.')
import psycopg2, json
from ai_integration.dynamic_catalog import dynamic_catalog
dynamic_catalog.refresh()

for sid in [4, 5, 6, 11, 18, 22, 23, 26, 28, 29]:
    s = dynamic_catalog.slices[sid]
    gb = s.get('groupby')
    gb_expr = None
    if gb and len(gb) > 0:
        g0 = gb[0]
        if isinstance(g0, dict):
            gb_expr = g0.get('sqlExpression') or g0.get('label')
        else:
            gb_expr = str(g0)
    
    dataset = s['dataset']
    custom_sql = dataset.get('custom_sql')
    from_clause = f"({custom_sql}) sub" if custom_sql else f"{dataset.get('schema') or 'goa'}.{dataset.get('table_name')}"
    where_conds = []
    for flt in s.get('adhoc_filters', []):
        subj = flt.get('subject')
        op = flt.get('operator')
        comp = flt.get('comparator')
        if not subj or comp == 'No filter' or comp is None:
            continue
        if op == 'NOT IN' and isinstance(comp, list):
            vals = ', '.join(f"'{v}'" for v in comp)
            where_conds.append(f"{subj} NOT IN ({vals})")
        elif op == 'IN' and isinstance(comp, list):
            vals = ', '.join(f"'{v}'" for v in comp)
            where_conds.append(f"{subj} IN ({vals})")
    where_str = f" WHERE {' AND '.join(where_conds)}" if where_conds else ''
    
    m = s.get('metric') or 'count'
    if isinstance(m, list) and m:
        m = m[0]
    m_sql = 'COUNT(*)'
    if isinstance(m, dict):
        m_sql = m.get('sqlExpression') or 'COUNT(*)'
    elif isinstance(m, str) and m not in ('count', '<new metric>'):
        m_sql = m
    
    db_uri = 'postgresql://dashboard_read_only_user:Zup1!whb@172.16.0.119:5432/' + ('org_db' if 'school' in dataset.get('table_name', '') else 'employee_db')
    conn = psycopg2.connect(db_uri)
    cur = conn.cursor()
    cur.execute(f"SELECT {m_sql} FROM {from_clause}{where_str}")
    tot = cur.fetchone()[0]
    bdown = {}
    if gb_expr:
        cur.execute(f"SELECT {gb_expr}, {m_sql} FROM {from_clause}{where_str} GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
        bdown = dict(cur.fetchall())
    print(f"Slice {sid} ({s['slice_name']}) => Total: {tot} | Breakdown: {bdown}")
    conn.close()
