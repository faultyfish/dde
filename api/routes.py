"""
api/routes.py
All API endpoints.

GET /jobs             — paginated, filterable job list
GET /jobs/{id}        — single job detail
GET /stats            — summary counts for dashboard
GET /scrape-runs      — last N scrape run logs
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from api.db import get_conn

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    category:   Optional[str] = Query(None),
    level:      Optional[str] = Query(None),
    remote_type:Optional[str] = Query(None),
    job_type:   Optional[str] = Query(None),
    visa:       Optional[bool] = Query(None),
    source:     Optional[str] = Query(None),
    stack:      Optional[str] = Query(None, description="Comma-separated stack keywords"),
    q:          Optional[str] = Query(None, description="Full-text search"),
    limit:      int = Query(50, le=200),
    offset:     int = Query(0),
):
    filters = ["is_active = TRUE"]
    params: list = []

    if category:
        filters.append(f"category = ${len(params)+1}")
        params.append(category)
    if level:
        filters.append(f"level = ${len(params)+1}")
        params.append(level)
    if remote_type:
        filters.append(f"remote_type = ${len(params)+1}")
        params.append(remote_type)
    if job_type:
        filters.append(f"job_type = ${len(params)+1}")
        params.append(job_type)
    if visa is not None:
        filters.append(f"visa_sponsor = ${len(params)+1}")
        params.append(visa)
    if source:
        filters.append(f"source = ${len(params)+1}")
        params.append(source)
    if stack:
        for kw in stack.split(","):
            kw = kw.strip()
            filters.append(f"${len(params)+1} = ANY(stack)")
            params.append(kw)
    if q:
        filters.append(
            f"(title ILIKE ${len(params)+1} OR company ILIKE ${len(params)+1} "
            f"OR description ILIKE ${len(params)+1})"
        )
        params.append(f"%{q}%")

    where = "WHERE " + " AND ".join(filters)
    sql = f"""
        SELECT id, external_id, source, title, company, location,
               remote_type, job_type, salary_raw, salary_min, salary_max,
               url, category, level, stack, visa_sponsor,
               first_seen_at, last_seen_at
        FROM jobs
        {where}
        ORDER BY last_seen_at DESC
        LIMIT ${len(params)+1} OFFSET ${len(params)+2}
    """
    params += [limit, offset]

    count_sql = f"SELECT COUNT(*) FROM jobs {where}"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(count_sql, params[:-2])
        total = cur.fetchone()["count"]

        cur.execute(sql, params)
        rows = cur.fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [dict(r) for r in rows],
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    sql = "SELECT * FROM jobs WHERE id = %s AND is_active = TRUE"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (job_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)


@router.get("/stats")
def stats():
    sql = """
        SELECT
            COUNT(*)                                        AS total,
            COUNT(*) FILTER (WHERE source = 'indeed')      AS indeed_count,
            COUNT(*) FILTER (WHERE source = 'linkedin')    AS linkedin_count,
            COUNT(*) FILTER (WHERE remote_type = 'Remote') AS remote_count,
            COUNT(*) FILTER (WHERE visa_sponsor = TRUE)    AS visa_count,
            COUNT(*) FILTER (WHERE category = 'DevOps')    AS devops_count,
            COUNT(*) FILTER (WHERE category = 'Cloud')     AS cloud_count,
            COUNT(*) FILTER (WHERE category = 'SRE')       AS sre_count,
            COUNT(*) FILTER (WHERE category = 'MLOps')     AS mlops_count,
            MAX(scraped_at)                                 AS last_scraped
        FROM jobs
        WHERE is_active = TRUE
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
    return dict(row)


@router.get("/scrape-runs")
def scrape_runs(limit: int = Query(10, le=50)):
    sql = """
        SELECT * FROM scrape_runs
        ORDER BY started_at DESC
        LIMIT %s
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]
