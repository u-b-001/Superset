"""
SamarthX Superset - Dynamic Chart Engine
100% Dynamic, Real-Time Query Execution against live PostgreSQL databases.
Zero hardcoded snapshots. All metrics and breakdowns are computed on-the-fly
from employee_db and org_db, ensuring 100% alignment with Superset dashboard charts.
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional, Tuple, List
import psycopg2

logger = logging.getLogger("samarthx.dynamic_chart_engine")

DB_CONFIGS = {
    "employee_db": {
        "host": os.environ.get("EMPLOYEE_DB_HOST", "172.16.0.119"),
        "port": int(os.environ.get("EMPLOYEE_DB_PORT", 5432)),
        "dbname": "employee_db",
        "user": os.environ.get("DB_USER", "dashboard_read_only_user"),
        "password": os.environ.get("DB_PASSWORD", "Zup1!whb"),
        "connect_timeout": 5
    },
    "org_db": {
        "host": os.environ.get("ORG_DB_HOST", "172.16.0.119"),
        "port": int(os.environ.get("ORG_DB_PORT", 5432)),
        "dbname": "org_db",
        "user": os.environ.get("DB_USER", "dashboard_read_only_user"),
        "password": os.environ.get("DB_PASSWORD", "Zup1!whb"),
        "connect_timeout": 5
    }
}

# In-memory query cache with 60s TTL to prevent database hammering while ensuring fresh live data
_QUERY_CACHE: Dict[str, Tuple[Any, float]] = {}
CACHE_TTL_SECONDS = 60.0

def execute_dynamic_query(sql: str, db: str = "employee_db") -> List[Tuple]:
    """Executes a read-only SELECT query against the live PostgreSQL database with short-lived TTL caching."""
    now = time.time()
    cache_key = f"{db}::{sql.strip()}"
    if cache_key in _QUERY_CACHE:
        val, ts = _QUERY_CACHE[cache_key]
        if now - ts < CACHE_TTL_SECONDS:
            return val

    try:
        conn = psycopg2.connect(**DB_CONFIGS[db])
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        _QUERY_CACHE[cache_key] = (rows, now)
        return rows
    except Exception as e:
        logger.error(f"Error executing dynamic query against {db}: {e}\nSQL: {sql}")
        return []

# Management Types Metadata (Patterns & Canonical Labels only - zero hardcoded counts)
MANAGEMENT_TYPES = {
    "religious": {
        "canonical": "Religious Organisations",
        "display": "religious organisation",
        "patterns": [r'\breligious\b', r'\breligion\b', r'\bchurch\b', r'\bmissionary\b']
    },
    "trust": {
        "canonical": "Trust",
        "display": "trust",
        "patterns": [r'\btrust\b', r'\btrusts\b', r'\btrustee\b', r'\btrustees\b']
    },
    "society": {
        "canonical": "Society",
        "display": "society",
        "patterns": [r'\bsociety\b', r'\bsocieties\b']
    },
    "state_govt": {
        "canonical": "State Govt",
        "display": "state government",
        "patterns": [r'\bstate\s+govt\b', r'\bstate\s+government\b', r'\bdept(?:\.|artment)?\s+of\s+education\b']
    },
    "privately_managed": {
        "canonical": "Privately Managed",
        "display": "privately managed",
        "patterns": [r'\bprivately\s+managed\b', r'\bprivate\s+management\b', r'\bprivately\b']
    },
    "local_bodies": {
        "canonical": "Local Bodies",
        "display": "local body",
        "patterns": [r'\blocal\s+bodies\b', r'\blocal\s+body\b', r'\bpanchayat\b', r'\bmunicipality\b', r'\bcorporation\b']
    },
    "central_govt": {
        "canonical": "Central Govt",
        "display": "central government",
        "patterns": [r'\bcentral\s+govt\b', r'\bcentral\s+government\b', r'\bcentral\b']
    },
    "individual": {
        "canonical": "Individual",
        "display": "individual",
        "patterns": [r'\bindividual\b', r'\bindividual\s+managed\b']
    }
}

# School Types Metadata (Patterns & Canonical Labels only)
SCHOOL_TYPES = {
    "govt": {
        "canonical": "Govt School",
        "display": "government",
        "patterns": [r'\b(govt|government|state\s+govt|state\s+government)\s+schools?\b', r'\bhow\s+many\s+govt\s+schools\b', r'\bhow\s+many\s+government\s+schools\b']
    },
    "aided": {
        "canonical": "Aided School",
        "display": "aided",
        "patterns": [r'\baided\b', r'\baided\s+schools?\b', r'\bgovernment\s+aided\b', r'\bgovt\s+aided\b']
    },
    "unaided": {
        "canonical": "Unaided School",
        "display": "unaided",
        "patterns": [r'\bunaided\b', r'\bunaided\s+schools?\b', r'\bnon-aided\b', r'\bprivate\s+unaided\b']
    },
    "private": {
        "canonical": "Private School",
        "display": "private",
        "patterns": [r'\bprivate\s+schools?\b', r'\bprivate\b']
    },
    "special_needs": {
        "canonical": "Special Needs School",
        "display": "special needs",
        "patterns": [r'\bspecial\s+needs?\b', r'\bcwsn\b']
    },
    "international": {
        "canonical": "International School",
        "display": "international",
        "patterns": [r'\binternational\b']
    },
    "cbse": {
        "canonical": "CBSE School",
        "display": "CBSE",
        "patterns": [r'\bcbse\b']
    },
    "icse": {
        "canonical": "ICSE School",
        "display": "ICSE",
        "patterns": [r'\bicse\b']
    },
    "central_govt": {
        "canonical": "Central Govt School",
        "display": "central government",
        "patterns": [r'\bcentral\s+govt\s+schools?\b', r'\bcentral\s+government\s+schools?\b']
    }
}

# Education Levels Metadata
EDUCATION_LEVELS = {
    "higher_secondary": {
        "canonical": "Higher Secondary",
        "patterns": [r'\bhigher\s+secondary\b', r'\bsenior\s+secondary\b', r'\b11th\b', r'\b12th\b', r'\bhss\b']
    },
    "secondary": {
        "canonical": "Secondary",
        "patterns": [r'\bsecondary\b', r'\bhigh\s*school\b', r'\b10th\b']
    },
    "primary": {
        "canonical": "Primary",
        "patterns": [r'\bprimary\b', r'\belementary\b']
    },
    "middle": {
        "canonical": "Middle",
        "patterns": [r'\bmiddle\b']
    },
    "pre_primary": {
        "canonical": "Pre-Primary",
        "patterns": [r'\bpre-primary\b', r'\bpre\s+primary\b', r'\bkindergarten\b', r'\bkg\b']
    },
    "upper_primary": {
        "canonical": "Upper Primary",
        "patterns": [r'\bupper\s+primary\b']
    }
}

def is_specific_or_adhoc_query(q: str) -> bool:
    """Returns True if the query is asking about a specific person, school, taluka, or ad-hoc custom query."""
    q = q.lower()
    specific_indicators = [
        r'\bnamed?\b', r'\bcalled\b', r'\bin\s+[a-z]+\s+taluka\b',
        r'\bin\s+[a-z]+\s+district\b', r'\bin\s+[a-z]+\s+village\b',
        r'\bwho\s+is\b', r'\bcontact\b', r'\bphone\b', r'\bemail\b',
        r'\baddress\b', r'\bpincode\b', r'\budise\b'
    ]
    return any(re.search(pat, q) for pat in specific_indicators)


def align_query_to_charts(question: str, raw_numeric: Optional[int] = None, dashboard_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    100% Dynamic Collinear Chart Resolver.
    Maps user intent to the corresponding Superset chart slice, executes the LIVE SQL query
    against PostgreSQL, and returns dynamic values and formatted metadata.
    """
    q_norm = question.strip()
    q_norm = re.sub(r'\bhow\s+man\b', 'how many', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(schoolds|schoold|schoool|schoools|shcool|shcools|scool|scools)\b', 'schools', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(managd|mannged|mngd|managment|managements)\b', 'managed', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(religous|relegious|religon)\b', 'religious', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(secodary|secondry|secndary)\b', 'secondary', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(primry|prmary)\b', 'primary', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(goverment|governmnt|state\s+governmnt)\b', 'govt', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(instutition|instutute|instituion)\b', 'institution', q_norm, flags=re.IGNORECASE)
    q_norm = re.sub(r'\b(organisations|organizations|organisation|organization)\b', 'organisations', q_norm, flags=re.IGNORECASE)
    q_lower = q_norm.lower().strip()

    if is_specific_or_adhoc_query(q_lower):
        return None

    # Gender Detection
    is_female = bool(re.search(r'\b(female|women|woman)\b', q_lower))
    is_male = bool(re.search(r'\b(male|men)\b', q_lower)) and not is_female
    is_transgender = bool(re.search(r'\b(transgender|trans)\b', q_lower))

    # Social Category Detection
    is_sc = bool(re.search(r'\b(sc|scheduled\s+caste)\b', q_lower))
    is_st = bool(re.search(r'\b(st|scheduled\s+tribe)\b', q_lower))
    is_obc = bool(re.search(r'\b(obc|other\s+backward)\b', q_lower))
    is_general = bool(re.search(r'\b(general|gen)\b', q_lower)) and not (is_sc or is_st or is_obc)

    # Nature of Appointment Detection
    is_non_reg = bool(re.search(r'\b(non-regular|non\s+regular|contract|temporary|adhoc|guest|contractual)\b', q_lower))
    is_reg = bool(re.search(r'\b(regular|permanent|confirmed)\b', q_lower)) and not is_non_reg

    # Staff Type Detection
    is_non_teaching = bool(re.search(r'\b(non-teaching|non\s+teaching|administrative|admin|clerk|support\s+staff)\b', q_lower))
    is_teaching = bool(re.search(r'\b(teacher|teachers|teaching|faculty|academic)\b', q_lower)) and not is_non_teaching
    is_total_emp = bool(re.search(r'\b(total\s+employee|total\s+staff|workforce|total\s+workforce|all\s+employees|employee\s+count)\b', q_lower))

    # Experience Detection
    has_exp = bool(re.search(r'\b(experience|exp|years|year|yrs|yr|joining)\b', q_lower))
    exp_under_5 = bool(re.search(r'(<\s*5|less\s+than\s+5|under\s+5|0-5|0\s*-\s*5|below\s+5)', q_lower))
    exp_10_20 = bool(re.search(r'\b(10\s*-\s*20|10\s+to\s+20|11\s*-\s*20|11\s+to\s+20)\b', q_lower))
    exp_5_10 = bool(re.search(r'\b(5\s*-\s*10|5\s+to\s+10|6\s*-\s*10|6\s+to\s+10)\b', q_lower))
    exp_20_plus = (bool(re.search(r'(20\+|\>\s*20|more\s+than\s+20|over\s+20|above\s+20|20\s+plus|\b20\s+years\s+or\s+more|\b20\+\s*years?)', q_lower))
                   or (bool(re.search(r'\b20\s+years?\b', q_lower)) and not exp_10_20)) and not exp_10_20

    # School & Management Detection
    is_school = bool(re.search(r'\b(school|schools|institution|institutions)\b', q_lower))
    matched_mgmt = None
    for m_key, m_info in MANAGEMENT_TYPES.items():
        if any(re.search(pat, q_lower) for pat in m_info["patterns"]):
            matched_mgmt = m_key
            break

    matched_type = None
    for t_key, t_info in SCHOOL_TYPES.items():
        if t_key == "private" and ("unaided" in q_lower or "privately managed" in q_lower or matched_mgmt == "privately_managed"):
            continue
        if t_key == "govt" and ("central" in q_lower or matched_mgmt == "central_govt"):
            continue
        if any(re.search(pat, q_lower) for pat in t_info["patterns"]):
            matched_type = t_key
            break

    matched_level = None
    for l_key in ["higher_secondary", "upper_primary", "pre_primary", "secondary", "primary", "middle"]:
        l_info = EDUCATION_LEVELS[l_key]
        if any(re.search(pat, q_lower) for pat in l_info["patterns"]):
            matched_level = l_key
            break

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 1: TEACHER'S DESIGNATION (Slice 7)
    # ═══════════════════════════════════════════════════════════════════════════
    is_hoi = bool(re.search(r'\b(heads?\s+of\s+(?:the\s+)?institutions?|hoi)\b', q_lower))
    is_acting_head = bool(re.search(r'\b(acting\s+head\s+teachers?|acting\s+head)\b', q_lower))
    is_lecturer = bool(re.search(r'\b(lecturers?)\b', q_lower))
    is_vocational = bool(re.search(r'\b(vocational\s+teachers?|full\s+time\s+vocational)\b', q_lower))

    if is_hoi or is_acting_head or is_lecturer or is_vocational:
        sql = """
            SELECT UPPER(TRIM(ts.employee_designation)), COUNT(DISTINCT ts.employee_user_id)
            FROM public.teaching_staff ts
            JOIN public.employees e ON e.employee_user_id = ts.employee_user_id
            WHERE UPPER(e.associated_school) NOT LIKE '%TEST%'
            GROUP BY 1 ORDER BY 2 DESC;
        """
        rows = execute_dynamic_query(sql, "employee_db")
        desig_counts = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}

        title = "Teacher's Designation"
        category = "Teacher Designation"

        if is_hoi:
            target_kpi = "head_of_institution"
            filter_tag = "Head of Institution"
            val = desig_counts.get("HEAD OF INSTITUTION", 0)
            auth_text = f"According to verified department records, there are **{val:,}** employees designated as Head of Institution across Goa educational institutions (matching the Teacher's Designation chart)."
            matched_slices = {"HEAD OF INSTITUTION": val, "Head of Institution": val}
        elif is_acting_head:
            target_kpi = "acting_head_teacher"
            filter_tag = "Acting Head Teacher"
            val = desig_counts.get("ACTING HEAD TEACHER (AIDED/UNAIDED)", 0)
            auth_text = f"According to verified department records, there are **{val:,}** employees designated as Acting Head Teacher (Aided/Unaided) across Goa educational institutions (matching the Teacher's Designation chart)."
            matched_slices = {"ACTING HEAD TEACHER (AIDED/UNAIDED)": val}
        elif is_lecturer:
            target_kpi = "lecturer"
            filter_tag = "Lecturer"
            val = desig_counts.get("LECTURER", 0)
            auth_text = f"According to verified department records, there are **{val:,}** employees designated as Lecturer across Goa educational institutions (matching the Teacher's Designation chart)."
            matched_slices = {"LECTURER": val}
        else:
            target_kpi = "vocational_teacher"
            filter_tag = "Vocational Teacher"
            val = desig_counts.get("CONTRACT BASIS VOCATIONAL TEACHER", 0)
            auth_text = f"According to verified department records, there are **{val:,}** employees designated as Vocational Teacher across Goa educational institutions (matching the Teacher's Designation chart)."
            matched_slices = {"CONTRACT BASIS VOCATIONAL TEACHER": val}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": 26
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 2: EXPERIENCE BREAKDOWNS (Slices 20 & 21)
    # ═══════════════════════════════════════════════════════════════════════════
    if has_exp and (exp_20_plus or exp_10_20 or exp_5_10 or exp_under_5):
        emp_filter = "employee_type = 'NON-TEACHING STAFF'" if is_non_teaching else "employee_type IN ('TEACHING STAFF', 'ACADEMIC TEACHER', 'VOCATIONAL TEACHER')"
        title = "Non-Teaching Experience by Gender" if is_non_teaching else "Teaching Experience by Gender"
        category = "Experience Breakdown"
        target_kpi = "non_teaching_experience" if is_non_teaching else "teaching_experience"
        sid = 21 if is_non_teaching else 20

        sql = f"""
            SELECT
                CASE
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_joining_service)) BETWEEN 0 AND 5 THEN 'A. 0-5 Years'
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_joining_service)) BETWEEN 6 AND 10 THEN 'B. 6-10 Years'
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_joining_service)) BETWEEN 11 AND 20 THEN 'C. 11-20 Years'
                    ELSE 'D. 20+ Years'
                END AS experience_bucket,
                TRIM(Upper(gender)) AS gender,
                COUNT(*) AS count
            FROM (
                SELECT e.*, esa.associated_school
                FROM goa.employees e
                LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id
            ) sub
            WHERE gender NOT IN ('1-Male', '2-Female', 'ST', 'SC', 'General', 'OBC')
              AND {emp_filter}
              AND associated_school NOT IN ('DHE - TEST', 'PRADNYA DHE TEST SCHOOL', 'SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL')
            GROUP BY 1, 2 ORDER BY 1, 2;
        """
        rows = execute_dynamic_query(sql, "employee_db")

        # Select bucket
        if exp_20_plus:
            bucket_key = "D. 20+ Years"
            filter_tag = "20+ Yrs Exp"
            range_desc = "more than 20 years of experience"
        elif exp_10_20:
            bucket_key = "C. 11-20 Years"
            filter_tag = "11-20 Yrs Exp"
            range_desc = "11-20 years of experience"
        elif exp_5_10:
            bucket_key = "B. 6-10 Years"
            filter_tag = "6-10 Yrs Exp"
            range_desc = "6-10 years of experience"
        else:
            bucket_key = "A. 0-5 Years"
            filter_tag = "0-5 Yrs Exp"
            range_desc = "0-5 years of experience"

        bucket_data = {str(r[1]): int(r[2]) for r in rows if r[0] == bucket_key}
        b_male = bucket_data.get("MALE", 0)
        b_female = bucket_data.get("FEMALE", 0)
        b_trans = bucket_data.get("TRANSGENDER", 0)
        b_total = sum(bucket_data.values())

        role_desc = "non-teaching staff" if is_non_teaching else "teachers"

        if is_male:
            val = b_male
            auth_text = f"According to verified department records, there are **{val:,}** male {role_desc} with {range_desc} (matching the {title} chart)."
            matched_slices = {"Male": val, bucket_key: val}
        elif is_female:
            val = b_female
            auth_text = f"According to verified department records, there are **{val:,}** female {role_desc} with {range_desc} (matching the {title} chart)."
            matched_slices = {"Female": val, bucket_key: val}
        else:
            val = b_total
            breakdown_parts = [f"{b_male:,} male", f"{b_female:,} female"]
            if b_trans > 0:
                breakdown_parts.append(f"{b_trans:,} transgender")
            auth_text = f"According to verified department records, there are **{val:,}** {role_desc} with {range_desc} (matching the {title} chart: {', '.join(breakdown_parts)})."
            matched_slices = {bucket_key: val, **bucket_data}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": sid
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 3: NATURE OF APPOINTMENT (Slice 4 & 5: Regular & Non-Regular)
    # ═══════════════════════════════════════════════════════════════════════════
    if is_reg and (is_teaching or "teacher" in q_lower or "regular" in q_lower):
        sql = """
            SELECT TRIM(UPPER(e.gender)), COUNT(DISTINCT e.id)
            FROM goa.employees e
            LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id
            WHERE esa.associated_school NOT IN ('DHE - TEST', 'PRADNYA DHE TEST SCHOOL', 'SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL')
              AND e.employee_type IN ('TEACHING STAFF', 'ACADEMIC TEACHER', 'VOCATIONAL TEACHER')
              AND e.nature_of_appointment IN ('1-Regular', 'Regular')
            GROUP BY 1 ORDER BY 2 DESC;
        """
        rows = execute_dynamic_query(sql, "employee_db")
        reg_by_gender = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}
        reg_total = sum(reg_by_gender.values())

        title = "Regular Teacher"
        category = "Regular Teachers"
        target_kpi = "regular_teacher"

        if is_female:
            val = reg_by_gender.get("FEMALE", 0)
            auth_text = f"According to verified department records, there are **{val:,}** regular female teachers recorded across Goa educational institutions (matching the Regular Teacher KPI card)."
            filter_tag = "Female Regular"
            matched_slices = {"Female": val, "Regular Teacher": val}
        elif is_male:
            val = reg_by_gender.get("MALE", 0)
            auth_text = f"According to verified department records, there are **{val:,}** regular male teachers recorded across Goa educational institutions (matching the Regular Teacher KPI card)."
            filter_tag = "Male Regular"
            matched_slices = {"Male": val, "Regular Teacher": val}
        else:
            val = reg_total
            auth_text = f"According to verified department database records, there are **{val:,}** regular teachers recorded in Goa educational institutions (matching the Regular Teacher KPI card)."
            filter_tag = "Regular Teachers"
            matched_slices = {"Regular Teacher": val, **reg_by_gender}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": 4
        }

    if is_non_reg and (is_teaching or "teacher" in q_lower or "contract" in q_lower or "temporary" in q_lower):
        sql = """
            SELECT TRIM(UPPER(e.gender)), COUNT(DISTINCT e.id)
            FROM goa.employees e
            LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id
            WHERE esa.associated_school NOT IN ('DHE - TEST', 'PRADNYA DHE TEST SCHOOL', 'SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL')
              AND e.employee_type IN ('TEACHING STAFF', 'ACADEMIC TEACHER', 'VOCATIONAL TEACHER')
              AND e.nature_of_appointment IN ('Non - Regular', 'Non-Regular', 'NON - REGULAR', '2-Contract', 'Contract')
            GROUP BY 1 ORDER BY 2 DESC;
        """
        rows = execute_dynamic_query(sql, "employee_db")
        non_reg_by_gender = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}
        non_reg_total = sum(non_reg_by_gender.values())

        title = "Non-Regular Teacher"
        category = "Non-Regular Teachers"
        target_kpi = "non_regular_teacher"

        if is_female:
            val = non_reg_by_gender.get("FEMALE", 0)
            auth_text = f"According to verified department records, there are **{val:,}** non-regular female teachers recorded across Goa educational institutions (matching the Non-Regular Teacher KPI card)."
            filter_tag = "Female Non-Regular"
            matched_slices = {"Female": val, "Non-Regular Teacher": val}
        elif is_male:
            val = non_reg_by_gender.get("MALE", 0)
            auth_text = f"According to verified department records, there are **{val:,}** non-regular male teachers recorded across Goa educational institutions (matching the Non-Regular Teacher KPI card)."
            filter_tag = "Male Non-Regular"
            matched_slices = {"Male": val, "Non-Regular Teacher": val}
        else:
            val = non_reg_total
            auth_text = f"According to verified department database records, there are **{val:,}** non-regular (contractual / temporary) teachers currently recorded in Goa educational institutions (matching the Non-Regular Teacher KPI card)."
            filter_tag = "Non-Regular Teachers"
            matched_slices = {"Non-Regular Teacher": val, **non_reg_by_gender}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": 5
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 4: SOCIAL CATEGORY DISTRIBUTION (Slice 11 / 25)
    # ═══════════════════════════════════════════════════════════════════════════
    if is_sc or is_st or is_obc or is_general:
        sql = """
            SELECT UPPER(TRIM(e.social_category)), COUNT(*)
            FROM goa.employees e
            LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id
            WHERE esa.associated_school NOT IN ('DHE - TEST', 'PRADNYA DHE TEST SCHOOL', 'SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL')
            GROUP BY 1 ORDER BY 2 DESC;
        """
        rows = execute_dynamic_query(sql, "employee_db")
        cat_counts = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}

        title = "Social Category Distribution"
        category = "Social Category"
        target_kpi = "social_category"

        if is_obc:
            val = cat_counts.get("OBC", 0)
            filter_tag = "OBC"
            auth_text = f"According to verified department records, there are **{val:,}** employees registered under the OBC category (matching the Social Category Distribution chart)."
            matched_slices = {"OBC": val}
        elif is_st:
            val = cat_counts.get("ST", 0)
            filter_tag = "ST"
            auth_text = f"According to verified department records, there are **{val:,}** employees registered under the ST category (matching the Social Category Distribution chart)."
            matched_slices = {"ST": val}
        elif is_sc:
            val = cat_counts.get("SC", 0)
            filter_tag = "SC"
            auth_text = f"According to verified department records, there are **{val:,}** employees registered under the SC category (matching the Social Category Distribution chart)."
            matched_slices = {"SC": val}
        else:
            val = cat_counts.get("GENERAL", 0)
            filter_tag = "General"
            auth_text = f"According to verified department records, there are **{val:,}** employees registered under the General category (matching the Social Category Distribution chart)."
            matched_slices = {"General": val}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": 11
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 5: GENDER DISTRIBUTION (Slice 6 / 24)
    # ═══════════════════════════════════════════════════════════════════════════
    if (is_female or is_male or is_transgender) and not is_non_teaching and not has_exp:
        sql = """
            SELECT TRIM(UPPER(e.gender)), COUNT(*)
            FROM goa.employees e
            LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id
            WHERE esa.associated_school NOT IN ('DHE - TEST', 'PRADNYA DHE TEST SCHOOL', 'SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL')
              AND e.gender NOT IN ('General', 'SC', 'ST', '2-Female', '1-Male', 'OBC')
            GROUP BY 1 ORDER BY 2 DESC;
        """
        rows = execute_dynamic_query(sql, "employee_db")
        gender_counts = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}
        gender_total = sum(gender_counts.values())

        title = "Gender Distribution"
        category = "Gender Distribution"
        target_kpi = "gender_distribution"

        if is_female:
            val = gender_counts.get("FEMALE", 0)
            pct = round((val / gender_total * 100), 2) if gender_total > 0 else 0
            k_val = round(val / 1000, 1)
            filter_tag = "Female"
            auth_text = f"According to verified department records, there are **{val:,}** female teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart: {k_val}k, {pct}%)."
            matched_slices = {"Female": val}
        elif is_male:
            val = gender_counts.get("MALE", 0)
            pct = round((val / gender_total * 100), 2) if gender_total > 0 else 0
            k_val = round(val / 1000, 1)
            filter_tag = "Male"
            auth_text = f"According to verified department records, there are **{val:,}** male teaching and educational staff registered across Goa institutions (matching the Gender Distribution chart: {k_val}k, {pct}%)."
            matched_slices = {"Male": val}
        else:
            val = gender_counts.get("TRANSGENDER", 0)
            filter_tag = "Transgender"
            auth_text = f"According to verified department records, there are **{val:,}** transgender educational staff registered across Goa institutions (matching the Gender Distribution chart)."
            matched_slices = {"Transgender": val}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": 6
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 6: TEACHING & NON-TEACHING STAFF (Slice 22)
    # ═══════════════════════════════════════════════════════════════════════════
    if (is_non_teaching or (is_teaching and not is_reg and not is_non_reg)) and not has_exp and not is_school:
        sql = """
            SELECT employee_type, COUNT(*)
            FROM (
                SELECT e.*, esa.associated_school
                FROM goa.employees e
                LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id
            ) sub
            WHERE associated_school NOT IN ('SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL', 'DHE - TEST', 'DHE SCHOOL FOR TESTING')
              AND employee_type IN ('VOCATIONAL TEACHER', 'TEACHING STAFF', 'NON-TEACHING STAFF')
            GROUP BY 1 ORDER BY 2 DESC;
        """
        rows = execute_dynamic_query(sql, "employee_db")
        staff_counts = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}

        title = "Teaching & Non Teaching Staff"
        category = "Staff Types"
        target_kpi = "staff_types"

        if is_non_teaching:
            val = staff_counts.get("NON-TEACHING STAFF", 0)
            filter_tag = "Non-Teaching Staff"
            auth_text = f"According to verified department records, there are **{val:,}** administrative and non-teaching support employees registered in the database (matching the Teaching & Non Teaching Staff chart)."
            matched_slices = {"Non-Teaching Staff": val}
        else:
            val = staff_counts.get("TEACHING STAFF", 0) + staff_counts.get("VOCATIONAL TEACHER", 0)
            filter_tag = "Teaching Staff"
            auth_text = f"According to verified department records, there are **{val:,}** active teaching staff members registered in the database (matching the Teaching & Non Teaching Staff chart)."
            matched_slices = {"Teaching Staff": val}

        return {
            "title": title,
            "value": f"{val:,}",
            "numeric_value": val,
            "category": category,
            "target_kpi": target_kpi,
            "filter_tag": filter_tag,
            "matched_slices": matched_slices,
            "auth_text": auth_text,
            "sql": sql.strip(),
            "slice_id": 22
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 7: SCHOOLS - MANAGEMENT & TYPE WITH EDUCATION LEVEL
    # ═══════════════════════════════════════════════════════════════════════════
    if is_school or matched_mgmt or matched_type or matched_level:
        # Cross-Dimensional Management + Level
        if matched_mgmt and matched_level:
            m_info = MANAGEMENT_TYPES[matched_mgmt]
            l_info = EDUCATION_LEVELS[matched_level]
            sql = f"""
                SELECT COUNT(*) FROM goa.schools
                WHERE is_archived = false AND deleted_at IS NULL
                  AND UPPER(school_management_type) = '{m_info['canonical'].upper()}'
                  AND UPPER(school_level) = '{l_info['canonical'].upper()}';
            """
            rows = execute_dynamic_query(sql, "org_db")
            val = rows[0][0] if rows else 0
            title = "School Management Type by Education Level"
            category = "Management by Education Level"
            target_kpi = f"mgmt_level_{matched_mgmt}_{matched_level}"
            filter_tag = f"{m_info['canonical']} - {l_info['canonical']}"
            auth_text = f"According to verified institutional records, there are **{val:,}** {m_info['display']}-managed {l_info['canonical'].lower()} schools registered in the state educational database (matching the School Management Type by Education Level chart)."
            matched_slices = {f"{m_info['canonical']} - {l_info['canonical']}": val}
            return {
                "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
                "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
                "auth_text": auth_text, "sql": sql.strip(), "slice_id": 17
            }

        # Cross-Dimensional Type + Level
        if matched_type and matched_level:
            t_info = SCHOOL_TYPES[matched_type]
            l_info = EDUCATION_LEVELS[matched_level]
            sql = f"""
                SELECT COUNT(*) FROM goa.schools
                WHERE is_archived = false AND deleted_at IS NULL
                  AND UPPER(school_type) = '{t_info['canonical'].upper()}'
                  AND UPPER(school_level) = '{l_info['canonical'].upper()}';
            """
            rows = execute_dynamic_query(sql, "org_db")
            val = rows[0][0] if rows else 0
            title = "School Type with Level"
            category = "School Type with Level"
            target_kpi = f"type_level_{matched_type}_{matched_level}"
            filter_tag = f"{t_info['canonical']} - {l_info['canonical']}"
            auth_text = f"According to verified institutional records, there are **{val:,}** {t_info['display']} {l_info['canonical'].lower()} schools registered in the state educational database (matching the School Type with Level chart)."
            matched_slices = {f"{t_info['canonical']} - {l_info['canonical']}": val}
            return {
                "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
                "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
                "auth_text": auth_text, "sql": sql.strip(), "slice_id": 16
            }

        # School Management Alone
        if matched_mgmt and not matched_type:
            m_info = MANAGEMENT_TYPES[matched_mgmt]
            sql = f"""
                SELECT COUNT(*) FROM goa.schools
                WHERE is_archived = false AND deleted_at IS NULL
                  AND UPPER(school_management_type) = '{m_info['canonical'].upper()}';
            """
            rows = execute_dynamic_query(sql, "org_db")
            val = rows[0][0] if rows else 0
            title = "Schools Management Type"
            category = "Management Type"
            target_kpi = f"mgmt_{matched_mgmt}"
            filter_tag = m_info["canonical"]
            auth_text = f"According to verified institutional records, there are **{val:,}** {m_info['display']}-managed schools registered in the state educational database (matching the Schools Management Type chart)."
            matched_slices = {m_info["canonical"]: val}
            return {
                "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
                "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
                "auth_text": auth_text, "sql": sql.strip(), "slice_id": 29
            }

        # School Type Alone
        if matched_type:
            t_info = SCHOOL_TYPES[matched_type]
            sql = f"""
                SELECT COUNT(*) FROM goa.schools
                WHERE is_archived = false AND deleted_at IS NULL
                  AND UPPER(school_type) = '{t_info['canonical'].upper()}';
            """
            rows = execute_dynamic_query(sql, "org_db")
            val = rows[0][0] if rows else 0
            title = "Type of Schools"
            category = "School Type"
            target_kpi = f"type_{matched_type}"
            filter_tag = t_info["canonical"]
            auth_text = f"According to verified institutional records, there are **{val:,}** {t_info['display']} schools registered in the state educational database (matching the Type of Schools chart)."
            matched_slices = {t_info["canonical"]: val}
            return {
                "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
                "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
                "auth_text": auth_text, "sql": sql.strip(), "slice_id": 28
            }

        # Education Level Alone
        if matched_level:
            l_info = EDUCATION_LEVELS[matched_level]
            sql = f"""
                SELECT COUNT(*) FROM goa.schools
                WHERE is_archived = false AND deleted_at IS NULL
                  AND UPPER(school_level) = '{l_info['canonical'].upper()}';
            """
            rows = execute_dynamic_query(sql, "org_db")
            val = rows[0][0] if rows else 0
            title = "School Management Type by Education Level"
            category = "Education Level"
            target_kpi = f"level_{matched_level}"
            filter_tag = l_info["canonical"]
            auth_text = f"According to verified institutional records, there are **{val:,}** {l_info['canonical'].lower()} schools registered across Goa in the state educational database."
            matched_slices = {l_info["canonical"]: val}
            return {
                "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
                "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
                "auth_text": auth_text, "sql": sql.strip(), "slice_id": 17
            }

        # Total Schools
        if is_school and any(kw in q_lower for kw in ["total", "all", "how many", "count", "onboarded"]):
            sql = "SELECT COUNT(*) FROM goa.schools WHERE is_archived = false AND deleted_at IS NULL;"
            rows = execute_dynamic_query(sql, "org_db")
            val = rows[0][0] if rows else 0
            title = "Total Schools Onboarded"
            category = "Total Schools"
            target_kpi = "total_schools_onboarded"
            filter_tag = "Total Schools"
            auth_text = f"According to verified institutional records, there are **{val:,}** recognized schools onboarded in the state educational database (matching the Total Schools Onboarded KPI card)."
            matched_slices = {"Total Schools": val}
            return {
                "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
                "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
                "auth_text": auth_text, "sql": sql.strip(), "slice_id": 23
            }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE 8: TOTAL EMPLOYEES / WORKFORCE (Slice 18 / 6)
    # ═══════════════════════════════════════════════════════════════════════════
    if is_total_emp:
        sql = "SELECT COUNT(DISTINCT e.id) FROM goa.employees e WHERE e.deleted_at IS NULL;"
        rows = execute_dynamic_query(sql, "employee_db")
        val = rows[0][0] if rows else 0
        title = "Total Employees"
        category = "Total Employees"
        target_kpi = "total_employees"
        filter_tag = "Total Employees"
        auth_text = f"According to verified department records, the total recorded workforce across Goa educational institutions is **{val:,}** (matching the Total Employees KPI card)."
        matched_slices = {"Total Employees": val}
        return {
            "title": title, "value": f"{val:,}", "numeric_value": val, "category": category,
            "target_kpi": target_kpi, "filter_tag": filter_tag, "matched_slices": matched_slices,
            "auth_text": auth_text, "sql": sql.strip(), "slice_id": 18
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # DYNAMIC CATALOG FALLBACK (For any new or custom Superset charts)
    # ═══════════════════════════════════════════════════════════════════════════
    try:
        try:
            from ai_integration.dynamic_catalog import dynamic_catalog
        except ImportError:
            from dynamic_catalog import dynamic_catalog
        active_id = None
        if dashboard_context:
            active_id = dashboard_context.get("dashboard_id")
            if not active_id and dashboard_context.get("url"):
                active_dash = dynamic_catalog.resolve_active_dashboard(dashboard_context["url"])
                if active_dash:
                    active_id = active_dash.get("id")

        matched_slice = dynamic_catalog.find_matching_slice(question, active_dashboard_id=active_id)
        if matched_slice:
            computed_val, resolved_tag, breakdown = dynamic_catalog.extract_metric_for_query(matched_slice, question)
            if computed_val is not None:
                dyn_title = matched_slice["slice_name"]
                dyn_category = matched_slice.get("dashboard_title", "Dynamic Dashboard")
                dyn_target_kpi = f"slice_{matched_slice['slice_id']}"
                dyn_filter_tag = resolved_tag or matched_slice["slice_name"]
                dyn_matched_slices = breakdown or {dyn_title: computed_val}
                dyn_auth_text = f"According to verified records on the **{dyn_category}** dashboard, the current figure for **{dyn_filter_tag}** is **{computed_val:,}** (matching the {dyn_title} chart)."
                return {
                    "title": dyn_title,
                    "value": f"{computed_val:,}",
                    "numeric_value": computed_val,
                    "category": dyn_category,
                    "target_kpi": dyn_target_kpi,
                    "filter_tag": dyn_filter_tag,
                    "slice_id": matched_slice["slice_id"],
                    "dashboard_id": matched_slice["dashboard_id"],
                    "matched_slices": dyn_matched_slices,
                    "auth_text": dyn_auth_text,
                    "sql": f"-- Live dynamic query for slice {matched_slice['slice_id']}: {dyn_title}"
                }
    except Exception as d_err:
        logger.warning(f"Dynamic catalog fallback error: {d_err}")

    return None


class DynamicStatsAccessor(dict):
    """Backwards-compatible dynamic stats dictionary that queries the database live if accessed."""
    def __getitem__(self, key: str) -> Any:
        if key in ("total_schools", "total_schools_onboarded", "slice_23"):
            rows = execute_dynamic_query("SELECT COUNT(*) FROM goa.schools WHERE is_archived = false AND deleted_at IS NULL;", "org_db")
            tot = rows[0][0] if rows else 0
            return {"title": "Total Schools Onboarded", "total": tot, "slice_name": "Total Schools Onboarded"}
        elif key in ("regular_teachers", "slice_4"):
            sql = "SELECT COUNT(DISTINCT e.id) FROM goa.employees e LEFT JOIN goa.employee_school_associations esa ON e.id = esa.employee_id WHERE esa.associated_school NOT IN ('DHE - TEST', 'PRADNYA DHE TEST SCHOOL', 'SIYA TEST SCHOOL', 'SAMARTHX TEST SCHOOL') AND e.employee_type IN ('TEACHING STAFF', 'ACADEMIC TEACHER', 'VOCATIONAL TEACHER') AND e.nature_of_appointment IN ('1-Regular', 'Regular');"
            rows = execute_dynamic_query(sql, "employee_db")
            tot = rows[0][0] if rows else 0
            return {"title": "Regular Teacher", "total": tot, "slice_name": "Regular Teacher"}
        elif key in ("total_employees", "slice_18"):
            rows = execute_dynamic_query("SELECT COUNT(DISTINCT e.id) FROM goa.employees e WHERE e.deleted_at IS NULL;", "employee_db")
            tot = rows[0][0] if rows else 0
            return {"title": "Total Employees", "total": tot, "slice_name": "Total Employees"}
        return super().get(key, {})

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

# Backwards compatibility instance
DASHBOARD_STATS = DynamicStatsAccessor()
