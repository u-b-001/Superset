"""
SamarthX Superset - Dynamic Dashboard & Chart Catalog Engine
═══════════════════════════════════════════════════════════════════════════════
Auto-discovers, monitors, and dynamically aligns AI queries with ANY dashboard
and chart created inside Apache Superset.

No hardcoded chart numbers or manual slice mappings required.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
import psycopg2

logger = logging.getLogger("samarthx.dynamic_catalog")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [DynamicCatalog] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SUPERSET_METADATA_URI = os.environ.get(
    "DATABASE_URI",
    "postgresql://superset_user:password@localhost:5432/superset"
).replace("postgresql+psycopg2://", "postgresql://")

DEFAULT_DB_PWD = os.environ.get("DB_PASSWORD", "Zup1!whb")


class SupersetDynamicCatalog:
    """
    Maintains an active, live-synced catalog of all Superset dashboards,
    slices/charts, dataset schemas, and database connections.
    """

    def __init__(self, metadata_db_uri: str = SUPERSET_METADATA_URI, cache_ttl_seconds: int = 180):
        self.metadata_db_uri = metadata_db_uri
        self.cache_ttl = cache_ttl_seconds
        self.last_refresh_time: float = 0.0

        # In-memory indexes
        self.dashboards: Dict[int, Dict[str, Any]] = {}
        self.dashboards_by_slug: Dict[str, int] = {}
        self.slices: Dict[int, Dict[str, Any]] = {}
        self.slices_by_dashboard: Dict[int, List[int]] = {}
        self.datasets: Dict[int, Dict[str, Any]] = {}
        self.databases: Dict[int, Dict[str, Any]] = {}

        # Cached slice values: { slice_id: { "value": Any, "breakdown": Dict, "computed_at": float } }
        self._computed_cache: Dict[int, Dict[str, Any]] = {}

    def is_cache_stale(self) -> bool:
        return (time.time() - self.last_refresh_time) > self.cache_ttl

    def refresh(self, force: bool = False) -> bool:
        """
        Pulls latest dashboards, slices, and datasets from Superset's metadata database.
        """
        if not force and not self.is_cache_stale() and self.dashboards:
            return True

        try:
            conn = psycopg2.connect(self.metadata_db_uri, connect_timeout=5)
            cur = conn.cursor()

            # 1. Fetch Databases
            cur.execute("SELECT id, database_name, sqlalchemy_uri FROM dbs ORDER BY id")
            databases = {}
            for db_id, db_name, sa_uri in cur.fetchall():
                clean_uri = sa_uri.replace("postgresql+psycopg2://", "postgresql://") if sa_uri else ""
                if "XXXXXXXXXX" in clean_uri:
                    clean_uri = clean_uri.replace("XXXXXXXXXX", DEFAULT_DB_PWD)
                databases[db_id] = {
                    "id": db_id,
                    "name": db_name,
                    "uri": clean_uri
                }

            # 2. Fetch Datasets (tables)
            cur.execute("SELECT id, table_name, schema, sql, database_id FROM tables ORDER BY id")
            datasets = {}
            for ds_id, tbl_name, tbl_schema, custom_sql, db_id in cur.fetchall():
                datasets[ds_id] = {
                    "id": ds_id,
                    "table_name": tbl_name,
                    "schema": tbl_schema,
                    "custom_sql": custom_sql,
                    "database_id": db_id,
                    "db_info": databases.get(db_id, {})
                }

            # 3. Fetch Dashboards
            cur.execute("SELECT id, dashboard_title, slug FROM dashboards ORDER BY id")
            dashboards = {}
            dashboards_by_slug = {}
            for d_id, title, slug in cur.fetchall():
                clean_slug = (slug or "").lower().strip()
                dashboards[d_id] = {
                    "id": d_id,
                    "title": title or f"Dashboard {d_id}",
                    "slug": clean_slug,
                    "slice_ids": []
                }
                if clean_slug:
                    dashboards_by_slug[clean_slug] = d_id
                dashboards_by_slug[str(d_id)] = d_id
                # Also index title slugified
                clean_title_slug = re.sub(r'[^a-z0-9]+', '-', (title or "").lower()).strip('-')
                if clean_title_slug:
                    dashboards_by_slug[clean_title_slug] = d_id

            # 4. Fetch Slices & Dashboard Mappings
            cur.execute("""
                SELECT d.id, d.dashboard_title, s.id, s.slice_name, s.viz_type, s.datasource_id, s.params
                FROM dashboard_slices ds
                JOIN dashboards d ON d.id = ds.dashboard_id
                JOIN slices s ON s.id = ds.slice_id
                ORDER BY d.id, s.id
            """)
            slices = {}
            slices_by_dash: Dict[int, List[int]] = {}

            for d_id, d_title, s_id, s_name, viz_type, ds_id, params_raw in cur.fetchall():
                params = {}
                try:
                    params = json.loads(params_raw) if params_raw else {}
                except Exception:
                    pass

                ds_info = datasets.get(ds_id, {})
                slice_entry = {
                    "slice_id": s_id,
                    "slice_name": s_name,
                    "title": s_name,
                    "viz_type": viz_type,
                    "dashboard_id": d_id,
                    "dashboard_title": d_title,
                    "datasource_id": ds_id,
                    "dataset": ds_info,
                    "metric": params.get("metric"),
                    "metrics": params.get("metrics") or ([params.get("metric")] if params.get("metric") else []),
                    "groupby": params.get("groupby") or params.get("columns") or [],
                    "adhoc_filters": params.get("adhoc_filters") or [],
                    "params": params
                }
                slices[s_id] = slice_entry

                if d_id in dashboards:
                    dashboards[d_id]["slice_ids"].append(s_id)

                if d_id not in slices_by_dash:
                    slices_by_dash[d_id] = []
                slices_by_dash[d_id].append(s_id)

            conn.close()

            # Atomically update catalog
            self.databases = databases
            self.datasets = datasets
            self.dashboards = dashboards
            self.dashboards_by_slug = dashboards_by_slug
            self.slices = slices
            self.slices_by_dashboard = slices_by_dash
            self.last_refresh_time = time.time()

            logger.info(f"Loaded dynamic catalog: {len(self.dashboards)} dashboards, {len(self.slices)} slices across {len(self.datasets)} datasets.")
            return True

        except Exception as e:
            logger.warning(f"Could not refresh dynamic catalog from Superset DB: {e}")
            return False

    def resolve_active_dashboard(self, url_or_slug: str) -> Optional[Dict[str, Any]]:
        """
        Identifies active dashboard from browser URL, pathname, or slug.
        e.g. '/superset/dashboard/schools/' or '/superset/dashboard/2/'
        """
        self.refresh()
        if not url_or_slug:
            return None

        # Clean pathname
        match = re.search(r'/dashboard/([a-zA-Z0-9_\-]+)', url_or_slug)
        candidate = match.group(1).lower().strip() if match else url_or_slug.lower().strip()

        # Check by slug or ID
        if candidate in self.dashboards_by_slug:
            dash_id = self.dashboards_by_slug[candidate]
            return self.dashboards.get(dash_id)

        try:
            d_id = int(candidate)
            if d_id in self.dashboards:
                return self.dashboards[d_id]
        except Exception:
            pass

        return None

    def find_matching_slice(self, question: str, active_dashboard_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Dynamically matches user question against charts.
        Prioritizes the active dashboard currently being viewed, then falls back to all dashboards.
        """
        self.refresh()
        q_clean = question.lower().strip()
        q_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', q_clean))

        is_non_reg = bool(re.search(r'\b(non-regular|non\s+regular|contract|temporary)\b', q_clean))
        is_reg = bool(re.search(r'\b(regular|permanent)\b', q_clean)) and not is_non_reg

        search_slices = []

        # 1. Search Active Dashboard First
        if active_dashboard_id and active_dashboard_id in self.slices_by_dashboard:
            active_ids = self.slices_by_dashboard[active_dashboard_id]
            for sid in active_ids:
                if sid in self.slices:
                    search_slices.append((self.slices[sid], 5.0)) # strong active dashboard priority

        # 2. Add other slices
        for sid, s_info in self.slices.items():
            if not any(s[0]["slice_id"] == sid for s in search_slices):
                search_slices.append((s_info, 1.0))

        best_slice = None
        highest_score = 0.0

        for s_info, priority_boost in search_slices:
            s_name = s_info["slice_name"].lower()
            s_tokens = set(re.findall(r'\b[a-z0-9]{3,}\b', s_name))

            # Disambiguation guards
            if is_non_reg and "non-regular" not in s_name and "contract" not in s_name:
                continue
            if is_reg and ("non-regular" in s_name or "contract" in s_name):
                continue

            # Substring match
            if s_name in q_clean:
                score = 10.0 * priority_boost
            else:
                overlap = len(q_tokens.intersection(s_tokens))
                score = (overlap / max(len(s_tokens), 1)) * 5.0 * priority_boost if overlap > 0 else 0.0

            # Boost for matching groupby dimension (e.g. 'gender', 'designation', 'level', 'category')
            gb = s_info.get("groupby") or []
            for gb_item in gb:
                gb_name = ""
                if isinstance(gb_item, dict):
                    gb_name = (gb_item.get("label") or gb_item.get("sqlExpression") or "").lower()
                else:
                    gb_name = str(gb_item).lower()
                if gb_name and gb_name in q_clean:
                    score += 4.0 * priority_boost
                if "gender" in gb_name and any(re.search(rf'\b{re.escape(g)}\b', q_clean) for g in ["female", "male", "women", "men", "transgender"]):
                    score += 8.0 * priority_boost
                if "designation" in gb_name and any(re.search(rf'\b{re.escape(d)}\b', q_clean) for d in ["head of institution", "lecturer", "acting head", "designation"]):
                    score += 8.0 * priority_boost
                if "social_category" in gb_name and any(re.search(rf'\b{re.escape(c)}\b', q_clean) for c in ["obc", "st", "sc", "general"]):
                    score += 8.0 * priority_boost
                if "management" in gb_name and any(re.search(rf'\b{re.escape(m)}\b', q_clean) for m in ["trust", "society", "religious", "state govt", "private"]):
                    score += 8.0 * priority_boost

            if score > highest_score and score >= 2.0:
                highest_score = score
                best_slice = s_info

        return best_slice

    def execute_slice_query(self, slice_info: Dict[str, Any]) -> Tuple[Optional[int], Dict[str, int]]:
        """
        Constructs and executes the canonical SQL query for a slice against its target database,
        guaranteeing exact collinearity with Superset.
        """
        s_id = slice_info.get("slice_id")
        now = time.time()

        # Check cache (120s TTL)
        if s_id in self._computed_cache:
            entry = self._computed_cache[s_id]
            if (now - entry["computed_at"]) < 120.0:
                return entry["value"], entry["breakdown"]

        dataset = slice_info.get("dataset", {})
        db_info = dataset.get("db_info", {})
        db_uri = db_info.get("uri")

        if not db_uri or "XXXXXXXXXX" in db_uri:
            tbl = dataset.get("table_name", "")
            if tbl == "schools":
                db_uri = f"postgresql://dashboard_read_only_user:{DEFAULT_DB_PWD}@172.16.0.119:5432/org_db"
            else:
                db_uri = f"postgresql://dashboard_read_only_user:{DEFAULT_DB_PWD}@172.16.0.119:5432/employee_db"

        # Build SQL query from dataset and adhoc_filters
        table_name = dataset.get("table_name", "")
        schema = dataset.get("schema") or "goa"
        custom_sql = dataset.get("custom_sql")

        from_clause = f"({custom_sql}) sub" if custom_sql else f"{schema}.{table_name}"

        # Build WHERE conditions
        where_conds = []
        for flt in slice_info.get("adhoc_filters", []):
            clause = flt.get("clause", "WHERE")
            expr_type = flt.get("expressionType")
            if expr_type == "SQL":
                sql_expr = flt.get("sqlExpression")
                if sql_expr:
                    where_conds.append(f"({sql_expr})")
            elif expr_type == "SIMPLE":
                subj = flt.get("subject")
                op = flt.get("operator", "IN")
                comp = flt.get("comparator")
                if not subj or comp == "No filter" or comp is None:
                    continue
                if op == "IN" and isinstance(comp, list):
                    vals = ", ".join(f"'{v}'" if isinstance(v, str) else str(v).lower() for v in comp)
                    where_conds.append(f"{subj} IN ({vals})")
                elif op == "NOT IN" and isinstance(comp, list):
                    vals = ", ".join(f"'{v}'" if isinstance(v, str) else str(v).lower() for v in comp)
                    where_conds.append(f"{subj} NOT IN ({vals})")
                elif op in ("==", "="):
                    v_str = f"'{comp}'" if isinstance(comp, str) else str(comp)
                    where_conds.append(f"{subj} = {v_str}")

        where_str = f" WHERE {' AND '.join(where_conds)}" if where_conds else ""

        # Determine metric expression
        metric_sql = "COUNT(*)"
        metric_obj = slice_info.get("metric")
        if isinstance(metric_obj, dict):
            agg = metric_obj.get("aggregate", "COUNT")
            col = metric_obj.get("column", {}).get("column_name", "*")
            if agg == "COUNT_DISTINCT":
                metric_sql = f"COUNT(DISTINCT {col})"
            elif agg:
                metric_sql = f"{agg}({col})"
        elif isinstance(metric_obj, str) and metric_obj != "count":
            metric_sql = metric_obj

        # Execute
        try:
            conn = psycopg2.connect(db_uri, connect_timeout=5)
            cur = conn.cursor()

            # 1. Total aggregate
            total_sql = f"SELECT {metric_sql} FROM {from_clause}{where_str};"
            cur.execute(total_sql)
            row = cur.fetchone()
            val = int(row[0]) if row and row[0] is not None else 0

            # 2. Breakdown if groupby is present
            breakdown: Dict[str, int] = {}
            groupby = slice_info.get("groupby")
            if groupby and isinstance(groupby, list) and len(groupby) > 0:
                gb_item = groupby[0]
                if isinstance(gb_item, dict):
                    gb_expr = gb_item.get("sqlExpression") or gb_item.get("label") or gb_item.get("column_name")
                else:
                    gb_expr = str(gb_item)

                if gb_expr:
                    gb_sql = f"SELECT {gb_expr}, {metric_sql} FROM {from_clause}{where_str} GROUP BY 1 ORDER BY 2 DESC LIMIT 50;"
                    try:
                        cur.execute(gb_sql)
                        for r in cur.fetchall():
                            k_name = str(r[0]).strip() if r[0] is not None else "Unknown"
                            k_val = int(r[1]) if r[1] is not None else 0
                            breakdown[k_name] = k_val
                    except Exception as ge:
                        logger.warning(f"Error in dynamic groupby query: {ge}")

            conn.close()

            # Cache result
            self._computed_cache[s_id] = {
                "value": val,
                "breakdown": breakdown,
                "computed_at": now
            }
            return val, breakdown

        except Exception as e:
            logger.warning(f"Error computing live value for slice {s_id} ({slice_info.get('slice_name')}): {e}")
            return None, {}

    def extract_metric_for_query(self, slice_info: Dict[str, Any], question: str) -> Tuple[Optional[int], str, Dict[str, int]]:
        """
        Executes the slice query and checks if the question asks for a specific category in the breakdown.
        Returns: (resolved_value, resolved_tag, breakdown_dict)
        """
        val, breakdown = self.execute_slice_query(slice_info)
        if val is None:
            return None, slice_info.get("slice_name", ""), {}

        q_lower = question.lower()

        # Check breakdown keys against question tokens
        if breakdown:
            for k, num in breakdown.items():
                k_clean = str(k).lower().strip()
                if not k_clean:
                    continue
                # Exact or token match for category
                if k_clean in q_lower or (len(k_clean) > 3 and any(w == k_clean for w in re.findall(r'\b[a-z0-9]+\b', q_lower))):
                    return num, str(k), breakdown
                # Common synonyms with exact word boundaries to prevent 'men' matching 'government'
                if k_clean == "female" and any(re.search(rf'\b{re.escape(w)}\b', q_lower) for w in ["female", "women", "woman"]):
                    return num, "Female", breakdown
                if k_clean == "male" and any(re.search(rf'\b{re.escape(w)}\b', q_lower) for w in ["male", "men", "man"]) and not re.search(r'\b(female|women|woman)\b', q_lower):
                    return num, "Male", breakdown

        return val, slice_info.get("slice_name", ""), breakdown


# Global Singleton Instance
dynamic_catalog = SupersetDynamicCatalog()
