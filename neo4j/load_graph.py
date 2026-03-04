"""
neo4j/load_graph.py
===================
Builds the Neo4j knowledge graph from 4 sources:

  1. Survey aggregates  — pulled from PostgreSQL
  2. WHO Atlas data     — downloaded from Our World in Data
  3. OSM Overpass API   — mental health facilities by country
  4. data.gov DCAT API  — government wellness program datasets
"""

import os
import io
import csv
import time
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

#neo4j connect
NEO4J_URI = os.getenv("NEO4J_URI",       "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "bridgewell123")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

def run(query, params = None):
    with driver.session() as session:
        return session.run(query, params or {})

#postgresql connect
def get_pg():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"), 
        port=os.getenv("PG_PORT", 5432),
        dbname=os.getenv("PG_DB", "bridgewell"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", ""),
    )

#loading survey aggregates from postgresql to neo4j
def load_survey_aggregates():
    print("\n[1/4] Loading survey aggregates from PostgreSQL to Neo4j...")
    pg = get_pg()
    cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM employer_gap_by_country")
    gap_rows = cur.fetchall()

    cur.execute("SELECT * FROM lifestyle_risk_by_country")
    lifestyle_rows = {r["country"]: r for r in cur.fetchall()}

    cur.execute("SELECT * FROM treatment_gap_by_country")
    treatment_rows = {r["country"]: r for r in cur.fetchall()}

    cur.close()
    pg.close()

    for row in gap_rows:
        country = row["country"]
        lf = lifestyle_rows.get(country, {})
        tx = treatment_rows.get(country, {})

        run("""
            MERGE (c:Country {name: $country})
            SET c.who_region = $who_region
            """, {
                "country":  country,
                "who_region": _who_region(country),
            })
        
        run("""
            MERGE (s:SurveySnapshot {country: $country})
            SET s.total_respondents     = $total,
                s.avg_stress            = $avg_stress,
                s.avg_work_life_balance = $avg_wlb,
                s.avg_job_satisfaction  = $avg_js,
                s.avg_symptom_score     = $avg_symptom,
                s.pct_lacking_support   = $pct_lacking,
                s.avg_sleep_hours       = $avg_sleep,
                s.avg_screen_time       = $avg_screen,
                s.pct_untreated         = $pct_untreated
            WITH s
            MATCH (c:Country {name: $country})
            MERGE (c)-[:HAS_SURVEY_DATA]-> (s)
        """, {
            "country":       country,
            "total":         row["total_respondents"],
            "avg_stress":    float(row["avg_stress"] or 0),
            "avg_wlb":       float(row["avg_work_life_balance"] or 0),
            "avg_js":        float(row["avg_job_satisfaction"] or 0),
            "avg_symptom":   float(row["avg_symptom_score"] or 0),
            "pct_lacking":   float(row["pct_lacking_support"] or 0),
            "avg_sleep":     float(lf.get("avg_sleep_hours") or 0),
            "avg_screen":    float(lf.get("avg_screen_time") or 0),
            "pct_untreated": float(tx.get("pct_untreated") or 0),
        })
        
        _create_needs_for_country(country, row, lf)

    print(f" {len(gap_rows)} countries loaded as Country + SurveySnapshot nodes")

#helper functions
def _create_needs_for_country(country, gap_row, lf_row):
    needs = []

    avg_stress = float(gap_row.get("avg_stress") or 0)
    avg_symptom = float(gap_row.get("avg_symptom_score") or 0)
    avg_sleep   = float(lf_row.get("avg_sleep_hours") or 7)
    avg_screen  = float(lf_row.get("avg_screen_time") or 0)

    if avg_stress >= 6.0:
        needs.append(("stress_management", "Stress Management", avg_stress))
    if avg_symptom >= 5.0:
        needs.append(("anxiety_depression", "Anxiety & Depression", avg_symptom))
    if avg_sleep < 6.5:
        needs.append(("sleep_health",       "Sleep Health",         avg_sleep))
    if avg_screen >= 7.0:
        needs.append(("digital_wellness",   "Digital Wellness",     avg_screen))
    if float(gap_row.get("pct_lacking_support") or 0) >= 60:
        needs.append(("employer_policy",    "Employer MH Policy",   None))

    for name, label, score in needs:
        run("""
            MERGE (n:MentalHealthNeed {name: $name})
            SET n.label = $label
            WITH n
            MATCH (c:Country {name: $country})
            MERGE (c)-[r:HAS_NEED]->(n)
            SET r.severity_score = $score
        """, {"name": name, "label": label, "country": country, "score": score})


def _who_region(country):
    mapping = {
        "USA":     "AMRO",
        "Brazil":  "AMRO",
        "UK":      "EURO",
        "Germany": "EURO",
        "India":   "SEARO",
        "Other":   "GLOBAL",
    }
    return mapping.get(country, "GLOBAL")

#WHO Atlas data
OWID_BASE = "https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true"

OWID_INDICATORS = [
    {
        "slug": "psychiatrists-working-in-the-mental-health-sector",
        "prop": "psychiatrists_per_100k",
    },
]

OWID_COUNTRY_MAP = {
    "United Kingdom": "UK",
    "Germany": "Germany",
    "Brazil": "Brazil",
}

def load_who_atlas():
    print("\n[2/4] Downloading WHO Atlas indicators from Our World in Data...")

    for indicator in OWID_INDICATORS:
        url = OWID_BASE.format(slug=indicator["slug"])
        print(f"  Fetching {indicator['slug']}...")

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f" Could not fetch {indicator['slug']}: {e}")
            _load_who_placeholder(indicator["prop"])
            continue

        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)

        meta_cols = {"entity", "code", "year"}
        data_cols = [c for c in reader.fieldnames if c not in meta_cols]
        value_col = data_cols[-1] if data_cols else None

        if not value_col:
            continue

        latest = {}
        for row in rows:
            entity = row.get("entity", "")
            mapped = OWID_COUNTRY_MAP.get(entity)
            if not mapped:
                continue
            try:
                year = int(row.get("year", 0))
                val = float(row.get(value_col, 0) or 0)
            except ValueError:
                continue
            if mapped not in latest or year > latest[mapped][0]:
                latest[mapped] = (year, val)
        
        for country, (year, val) in latest.items():
            run(f"""
                MERGE (w:WHOProfile {{country_name: $country}})
                SET w.{indicator['prop']} = $val,
                    w.{indicator['prop']}_year = $year
                WITH w
                MATCH (c:Country {{name: $country}})
                MERGE (c)-[:HAS_WHO_PROFILE]-> (w)
            """, {"country": country, "val": val, "year": year})
        
        print(f" {indicator['prop']} loaded for {len(latest)} countries")
    
    time.sleep(1)
    _load_who_placeholder("mh_budget_pct")
    _load_who_placeholder("has_mh_policy")

def _load_who_placeholder(prop):
    placeholders = {
       "psychiatrists_per_100k": {
            "USA": 16.0, "UK": 14.0, "Germany": 27.0,
            "India": 0.3, "Brazil": 3.2, "Other": 1.0,
        },
        "mh_budget_pct": {
            "USA": 5.5, "UK": 10.8, "Germany": 11.3,
            "India": 0.06, "Brazil": 2.3, "Other": 1.0,
        },
        "has_mh_policy": {
            "USA": 1, "UK": 1, "Germany": 1,
            "India": 1, "Brazil": 1, "Other": 0,
        },
    }
    data = placeholders.get(prop, {})
    for country, val in data.items():
        run(f"""
            MERGE (w:WHOProfile {{country_name: $country}})
            SET w.{prop} = $val
            WITH w
            MATCH (c:Country {{name: $country}})
            MERGE (c)-[:HAS_WHO_PROFILE]->(w)
        """, {"country": country, "val": val}) 


#OSM Overpass api for facilities
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

COUNTRY_BBOXES = {
    "USA":     (24.396308, -125.0, 49.384358, -66.93457),
    "UK":      (49.9, -8.0, 60.85, 2.0),
    "Germany": (47.3, 5.9, 55.0, 15.0),
    "India":   (6.5, 68.0, 35.5, 97.5),
    "Brazil":  (-33.8, -73.9, 5.3, -29.3),
}

def load_osm_facilities():
    print("\n[3/4] Querying OSM Overpass API for facilities...")

    for country, bbox in COUNTRY_BBOXES.items():
        s, w, n, e = bbox
        bbox_str = f"{s},{w},{n},{e}"

        query = f"""
        [out:json][timeout:30];
        (
          node["amenity"="clinic"]["healthcare"="psychiatry"]({bbox_str});
          node["amenity"="clinic"]["healthcare"="psychologist"]({bbox_str});
          node["leisure"="fitness_centre"]({bbox_str});
          node["amenity"="meditation_centre"]({bbox_str});
          node["healthcare"="psychotherapist"]({bbox_str});
        );
        out center 50;
        """

        print(f"  Querying OSM for {country}...", end=" ")
        try:
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=45)
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
        except requests.RequestException as e:
            print(f" failed ({e})")
            continue

        loaded = 0
        for el in elements:
            tags   = el.get("tags", {})
            osm_id = str(el.get("id", ""))
            lat    = el.get("lat") or el.get("center", {}).get("lat")
            lon    = el.get("lon") or el.get("center", {}).get("lon")
            name   = tags.get("name", "Unknown Facility")
            category = _classify_osm(tags)

            run("""
                MERGE (f:Facility {osm_id: $osm_id})
                SET f.name     = $name,
                    f.category = $category,
                    f.lat      = $lat,
                    f.lon      = $lon,
                    f.country  = $country
                WITH f
                MATCH (c:Country {name: $country})
                MERGE (c)-[:HAS_FACILITY]->(f)
            """, {
                "osm_id":   osm_id,
                "name":     name,
                "category": category,
                "lat":      lat,
                "lon":      lon,
                "country":  country,
            })
            loaded += 1

        print(f"{loaded} facilities loaded")
        time.sleep(10)

    print("  OSM facilities loaded")


def _classify_osm(tags):
    amenity    = tags.get("amenity", "")
    leisure    = tags.get("leisure", "")
    healthcare = tags.get("healthcare", "")

    if healthcare in ("psychiatry", "psychologist"):
        return "mental_health_clinic"
    if amenity in ("clinic", "hospital"):
        return "general_clinic"
    if leisure == "fitness_centre":
        return "gym"
    if amenity == "meditation_centre":
        return "meditation_centre"
    return "wellness_centre"


#data.gov dcat api
DATAGOV_API = "https://catalog.data.gov/api/3/action/package_search"

SEARCH_TERMS = [
    "workplace mental health",
    "employee wellness program",
    "workplace stress",
    "mental health treatment",
    "EAP employee assistance",
]

def load_datagov_programs():
    print("\n[4/4] Querying data.gov DCAT API for government program datasets...")

    seen_ids = set()

    for term in SEARCH_TERMS:
        print(f"  Searching: '{term}'...", end=" ")
        try:
            resp = requests.get(DATAGOV_API, params={
                "q":    term,
                "rows": 10,
            }, timeout=20)
            resp.raise_for_status()
            results = resp.json().get("result", {}).get("results", [])
        except requests.RequestException as e:
            print(f"  failed ({e})")
            continue

        loaded = 0
        for pkg in results:
            identifier = pkg.get("id", "")
            if not identifier or identifier in seen_ids:
                continue
            seen_ids.add(identifier)

            title        = pkg.get("title", "")
            publisher    = pkg.get("organization", {}).get("title", "Unknown")
            desc         = (pkg.get("notes", "") or "")[:500]
            url          = f"https://catalog.data.gov/dataset/{pkg.get('name','')}"
            tags         = [t.get("name", "") for t in pkg.get("tags", [])]
            program_type = _classify_dataset(title, tags)

            run("""
                MERGE (d:GovDataset {identifier: $id})
                SET d.title        = $title,
                    d.publisher    = $publisher,
                    d.description  = $desc,
                    d.url          = $url,
                    d.program_type = $program_type
            """, {
                "id":           identifier,
                "title":        title,
                "publisher":    publisher,
                "desc":         desc,
                "url":          url,
                "program_type": program_type,
            })

            if program_type:
                run("""
                    MATCH (d:GovDataset {identifier: $id})
                    MATCH (p:WellbeingProgram {program_type: $program_type})
                    MERGE (p)-[:EVIDENCED_BY]->(d)
                """, {"id": identifier, "program_type": program_type})

            loaded += 1

        print(f"{loaded} new datasets")
        time.sleep(0.5)

    print(f"  {len(seen_ids)} government datasets loaded as GovDataset nodes")


def _classify_dataset(title, tags):
    title_lower = title.lower()
    tag_str     = " ".join(tags).lower()
    text        = title_lower + " " + tag_str

    if any(w in text for w in ["eap", "employee assistance", "counseling"]):
        return "EAP"
    if any(w in text for w in ["mindfulness", "meditation", "stress reduction"]):
        return "mindfulness"
    if any(w in text for w in ["fitness", "exercise", "physical activity"]):
        return "fitness"
    if any(w in text for w in ["sleep", "fatigue"]):
        return "sleep_hygiene"
    if any(w in text for w in ["substance", "alcohol", "drug"]):
        return "substance_support"
    if any(w in text for w in ["policy", "legislation", "workplace law"]):
        return "employer_policy"
    return None

#seed wellbeing program nodes
PROGRAMS = [
    {
        "program_id":   "EAP_001",
        "name":         "Employee Assistance Program (EAP)",
        "program_type": "EAP",
        "description":  "Confidential short-term counseling and referrals for employees with personal and work-related problems.",
        "addresses":    ["stress_management", "anxiety_depression", "employer_policy"],
        "remote_ok":    True,
    },
    {
        "program_id":   "MIND_001",
        "name":         "Mindfulness-Based Stress Reduction (MBSR)",
        "program_type": "mindfulness",
        "description":  "8-week structured program teaching mindfulness meditation to reduce stress and anxiety.",
        "addresses":    ["stress_management", "anxiety_depression", "sleep_health"],
        "remote_ok":    True,
    },
    {
        "program_id":   "FIT_001",
        "name":         "Workplace Fitness & Movement Program",
        "program_type": "fitness",
        "description":  "Subsidized gym access and on-site fitness classes to improve physical and mental health.",
        "addresses":    ["stress_management", "sleep_health"],
        "remote_ok":    False,
    },
    {
        "program_id":   "SLEEP_001",
        "name":         "Sleep Health & Hygiene Program",
        "program_type": "sleep_hygiene",
        "description":  "Digital CBT-I based sleep improvement program with personalized coaching.",
        "addresses":    ["sleep_health", "anxiety_depression"],
        "remote_ok":    True,
    },
    {
        "program_id":   "DIGWEL_001",
        "name":         "Digital Wellness & Screen Time Program",
        "program_type": "digital_wellness",
        "description":  "Structured program to reduce harmful screen use and build healthier digital habits.",
        "addresses":    ["digital_wellness", "sleep_health", "anxiety_depression"],
        "remote_ok":    True,
    },
    {
        "program_id":   "POLICY_001",
        "name":         "Mental Health Policy & Manager Training",
        "program_type": "employer_policy",
        "description":  "Training managers to recognize mental health issues and implementing formal MH policies.",
        "addresses":    ["employer_policy", "stress_management"],
        "remote_ok":    True,
    },
    {
        "program_id":   "PEER_001",
        "name":         "Peer Support & Mental Health Champions",
        "program_type": "peer_support",
        "description":  "Training designated employees as mental health first aiders and peer support contacts.",
        "addresses":    ["anxiety_depression", "employer_policy"],
        "remote_ok":    True,
    },
]

def load_programs():
    print("\n[5/5] Seeding WellbeingProgram nodes...")
    for prog in PROGRAMS:
        run("""
            MERGE (p:WellbeingProgram {program_id: $program_id})
            SET p.name         = $name,
                p.program_type = $program_type,
                p.description  = $description,
                p.remote_ok    = $remote_ok
        """, {k: prog[k] for k in ["program_id", "name", "program_type", "description", "remote_ok"]})

        for need_name in prog["addresses"]:
            run("""
                MATCH (p:WellbeingProgram {program_id: $program_id})
                MERGE (n:MentalHealthNeed {name: $need})
                MERGE (p)-[:ADDRESSES]->(n)
            """, {"program_id": prog["program_id"], "need": need_name})

    print(f" {len(PROGRAMS)} programs seeded with ADDRESSES relationships")


#running it all
if __name__ == "__main__":
    print("=" * 60)
    print("BridgeWell - Neo4j Graph Loader")
    print("=" * 60)

    load_survey_aggregates()
    load_who_atlas()
    load_osm_facilities()
    load_datagov_programs()
    load_programs()

    driver.close()
    print("\n Graph fully loaded.")
    print("\n Sample verification query to run in Neo4j Brower:")
    print(" MATCH (c:Country)-[:HAS_NEED]->(n)<-[:ADDRESSES]-(p:WellbeingProgram)")
    print(" RETURN c.name, n.label, p.name LIMIT 20")