"""
api/main.py
===========
BridgeWell FastAPI application.

ENDPOINTS:
  GET  /                          - Health check
  GET  /countries                 - List all countries
  GET  /analysis/{country}        - SQL aggregate analysis
  GET  /recommendations/{country} - Neo4j program recommendations
  GET  /graph/{country}           - Full graph view for visualization
  POST /company                   - Register company + get recommendations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional

from .db import pg_query, neo4j_query, close_connections

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_connections()

app = FastAPI(
    title="BridgeWell",
    description="Connect employers to employee wellbeing programs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#models and first route
class CompanyInput(BaseModel):
    name:           str
    country:        str
    industry:       str
    size:           str
    remote_policy:  str
    company_id:     Optional[str] = None

@app.get("/")
def health():
    return {"status": "ok", "service": "BridgeWell API"}

@app.get("/countries")
def list_countries():
    rows = pg_query("SELECT DISTINCT country FROM respondents ORDER BY country")
    return {"countries": [r["country"] for r in rows]}

@app.get("/analysis/{country}")
def country_analysis(country: str):
    gap = pg_query(
        "SELECT * FROM employer_gap_by_country WHERE country = %s",
        (country,)
    )
    if not gap:
        raise HTTPException(status_code=404, detail=f"Country '{country}' not found")
    
    lifestyle = pg_query(
        "SELECT * FROM lifestyle_risk_by_country WHERE country = %s",
        (country,)
    )
    treatment = pg_query(
        "SELECT * FROM treatment_gap_by_country WHERE country = %s",
        (country,)
    )

    return {
        "country":          country,
        "employer_gap":     gap[0]      if gap      else{},
        "lifestyle_risk":   lifestyle[0] if lifestyle   else{},
        "treatment_gap":    treatment[0] if treatment   else{},
    }

#recommendations and graph routes
@app.get("/recommendations/{country}")
def get_recommendations(country: str, remote_only: bool = False):
    remote_filter = "AND p.remote_ok = true" if remote_only else ""

    cypher = f"""
        MATCH (c:Country {{name: $country}})-[hn:HAS_NEED]->(n:MentalHealthNeed)
              <-[:ADDRESSES]-(p:WellbeingProgram)
        WHERE 1=1 {remote_filter}
        WITH p,
             collect(n.label)            AS addressed_needs,
             collect(hn.severity_score)  AS severity_scores,
             count(n)                    AS coverage_score
        OPTIONAL MATCH (p)-[:EVIDENCED_BY]->(d:GovDataset)
        WITH p, addressed_needs, severity_scores, coverage_score,
             collect(d.title) AS gov_datasets
        RETURN p.program_id    AS program_id,
               p.name          AS name,
               p.program_type  AS program_type,
               p.description   AS description,
               p.remote_ok     AS remote_ok,
               addressed_needs,
               coverage_score,
               gov_datasets
        ORDER BY coverage_score DESC
    """

    programs = neo4j_query(cypher, {"country": country})

    if not programs:
        exists = neo4j_query(
            "MATCH (c:Country {name: $country}) RETURN c.name",
            {"country": country}
        )
        if not exists:
            raise HTTPException(status_code=404, detail=f"Country '{country}' not in graph")
        return {"country": country, "programs": [], "message": "No needs identified"}

    who = neo4j_query("""
        MATCH (c:Country {name: $country})-[:HAS_WHO_PROFILE]->(w:WHOProfile)
        RETURN w.psychiatrists_per_100k AS psychiatrists_per_100k,
               w.mh_budget_pct         AS mh_budget_pct,
               w.has_mh_policy         AS has_mh_policy
    """, {"country": country})

    return {
        "country":     country,
        "who_context": who[0] if who else {},
        "programs":    programs,
    }


@app.get("/graph/{country}")
def get_country_graph(country: str):
    cypher = """
        MATCH (c:Country {name: $country})
        OPTIONAL MATCH (c)-[:HAS_SURVEY_DATA]->(s:SurveySnapshot)
        OPTIONAL MATCH (c)-[:HAS_WHO_PROFILE]->(w:WHOProfile)
        OPTIONAL MATCH (c)-[hn:HAS_NEED]->(n:MentalHealthNeed)<-[:ADDRESSES]-(p:WellbeingProgram)
        OPTIONAL MATCH (c)-[:HAS_FACILITY]->(f:Facility)
        RETURN c, s, w,
               collect(DISTINCT {need: n, severity: hn.severity_score}) AS needs,
               collect(DISTINCT p) AS programs,
               collect(DISTINCT f) AS facilities
    """
    rows = neo4j_query(cypher, {"country": country})
    if not rows:
        raise HTTPException(status_code=404, detail=f"Country '{country}' not found")

    row = rows[0]
    return {
        "country":    dict(row["c"]) if row["c"] else {},
        "survey":     dict(row["s"]) if row["s"] else {},
        "who":        dict(row["w"]) if row["w"] else {},
        "needs":      [{"need": dict(n["need"]), "severity": n["severity"]} for n in row["needs"] if n["need"]],
        "programs":   [dict(p) for p in row["programs"] if p],
        "facilities": [dict(f) for f in row["facilities"] if f],
    }

#company registration endpoint
@app.post("/company")
def register_company(company: CompanyInput):
    import uuid
    company_id = company.company_id or str(uuid.uuid4())[:8].upper()

    neo4j_query("""
        MERGE (co:Company {company_id: $company_id})
        SET co.name         = $name,
            co.industry     = $industry, 
            co.size         = $size,
            co.remote_policy = $remote_policy
        WITH co
        MATCH (c:Country {name: $country})
        MERGE (co)-[:LOCATED_IN]->(c)
    """, {
        "company_id":       company_id,
        "name":             company.name,
        "industry":         company.industry,
        "size":             company.size,
        "remote_policy":    company.remote_policy,
        "country":          company.country,
    })

    analysis_rows = pg_query(
        "SELECT * FROM employer_gap_by_country WHERE country =%s",
        (company.country,)
    )
    analysis = analysis_rows[0] if analysis_rows else{}

    remote_only = company.remote_policy == "yes"
    recs = get_recommendations(company.country, remote_only=remote_only)

    return {
        "company_id":   company_id,
        "company_name": company.name,
        "country":      company.country,
        "country_context": {
            "avg_stress":          analysis.get("avg_stress"),
            "pct_lacking_support": analysis.get("pct_lacking_support"),
            "avg_symptom_score":   analysis.get("avg_symptom_score"),
        },
        "recommendations": recs.get("programs", []),
        "who_context":     recs.get("who_context", {}),
    }