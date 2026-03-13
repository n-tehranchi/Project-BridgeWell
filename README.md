# DSC 202 Final Project

## Mental Health Employer Support Tool (BridgeWell)

**Group 6**:  
Natalie Tehranachi,  
Mitra Rezvany,  
Sruthi Papanasa,  
Diana Freeman  

---

# Project Overview

Mental health challenges in the workplace are increasingly recognized as a major factor affecting employee wellbeing, productivity, and retention. However, many employers struggle to identify appropriate mental health programs or interventions that effectively address the needs of their workforce.

The **Mental Health Employer Support Tool (BridgeWell)** is designed to help employers identify and implement evidence-based mental health and wellness programs tailored to their country and workforce context. The system integrates survey data, global health statistics, public wellness program datasets, and facility information to provide recommendations for employer wellness initiatives.

The application combines **relational database analytics and graph-based recommendation modeling**. Survey data and structured workforce information are stored in PostgreSQL, while relationships between mental health needs, countries, programs, and resources are modeled using Neo4j. A **FastAPI backend** integrates these components and exposes REST endpoints for country analysis, recommendation generation, graph visualization, and company registration. The current API is titled **BridgeWell**, version **1.0.0**, and is configured with permissive CORS settings to support frontend integration. :contentReference[oaicite:2]{index=2}

The intended users of this tool include:

* Employers and HR teams looking to improve workplace mental health support
* Researchers analyzing mental health patterns across countries
* Organizations seeking evidence-based employee wellness programs

The overall goal is to bridge the gap between **employee mental health needs and accessible workplace wellness programs**.

---

# Dataset Overview

The system integrates multiple data sources to support analysis and recommendations.

### 1. Survey Dataset (Primary Data)

The primary dataset contains survey responses related to mental health, workplace conditions, and lifestyle factors. Each respondent provides demographic, work environment, lifestyle, and mental health information.

Key categories include:

**Demographics**

* Age
* Gender
* Country
* Education level
* Marital status
* Income level

**Work Environment**

* Employment status
* Work hours per week
* Remote work status
* Job satisfaction
* Work stress level
* Workplace bullying
* Employer mental health support

**Lifestyle Factors**

* Exercise frequency
* Sleep hours
* Caffeine consumption
* Alcohol frequency
* Screen time
* Social media usage
* Diet quality

**Mental Health Indicators**

* Depression symptoms
* Anxiety indicators
* Mood instability
* Sleep difficulties
* Self-harm thoughts
* Treatment history

A **composite symptom score** is calculated from mental health indicators to measure overall psychological distress.

---

### 2. External Data Sources

Additional datasets enrich the system:

**WHO Atlas Indicators**

* Mental health workforce statistics (for example, psychiatrists per 100k population)
* Mental health policy indicators
* National mental health budget estimates

**OpenStreetMap (OSM) Data**

* Mental health clinics
* Psychotherapy providers
* Fitness centers
* Meditation centers

**Data.gov Public Datasets**

Government datasets related to:

* Workplace mental health programs
* Employee assistance programs
* Wellness initiatives
* Mental health policy

These sources provide contextual information used in the graph-based recommendation system.

---

# Relational Database Design

A **PostgreSQL relational database** is used to store structured survey data and support statistical analysis queries.

Relational databases are ideal for:

* Structured tabular data
* Efficient aggregation queries
* Data integrity through constraints
* Transaction management

### Core Tables

#### Respondents

Stores demographic information for each survey participant.

Primary Key:

* `respondent_id`

Key attributes:

* age
* gender
* country
* education
* family_history_mental_illness
* social_support

---

#### Work Profiles

Stores employment and workplace characteristics.

Foreign Key:

* `respondent_id → respondents.respondent_id`

Attributes include:

* employment_status
* work_hours_per_week
* job_satisfaction
* work_stress_level
* company_mental_health_support
* financial_stress

---

#### Lifestyle Factors

Captures daily behaviors affecting mental health.

Foreign Key:

* `respondent_id`

Attributes include:

* exercise_per_week
* sleep_hours_per_night
* alcohol_frequency
* smoking
* screen_time_hours_day
* diet_quality

---

#### Mental Health Status

Tracks mental health symptoms and treatment history.

Foreign Key:

* `respondent_id`

Includes symptom indicators such as:

* feeling_sad_down
* anxiety
* mood_swings
* panic_attacks
* suicidal_thoughts

A **generated column** computes the composite mental health symptom score across all indicators.

---

### Analytical Views

Aggregated SQL views support the analysis API endpoints.

Examples include:

* **employer_gap_by_country**
* **lifestyle_risk_by_country**
* **treatment_gap_by_country**

These views calculate metrics such as:

* average stress level
* work-life balance scores
* percentage of respondents lacking employer support
* untreated mental health rates

These aggregated metrics feed into the graph model and are used directly by the `/analysis/{country}` and `/company` endpoints. :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4}

---

# Graph Database Design

A **Neo4j graph database** models relationships between countries, mental health needs, programs, and resources.

Graph databases are well suited for:

* relationship-based reasoning
* recommendation systems
* multi-source data integration

### Node Types

**Country**  
Represents each country included in the survey.

**SurveySnapshot**  
Stores aggregated mental health metrics derived from the relational database.

**MentalHealthNeed**  
Represents identified needs such as:

* Stress management
* Anxiety and depression support
* Sleep health
* Digital wellness
* Employer policy improvements

**WellbeingProgram**  
Represents employer wellness interventions such as:

* Employee Assistance Programs (EAP)
* Mindfulness training
* Fitness programs
* Sleep hygiene programs
* Digital wellness programs

**WHOProfile**  
Stores country-level public health indicators.

**Facility**  
Represents mental health services and wellness facilities.

**GovDataset**  
Public datasets providing evidence supporting wellness programs.

**Company**  
Represents an employer registered through the API. Company nodes are linked to a country and used to return tailored recommendations. :contentReference[oaicite:5]{index=5}

---

### Relationships

Key graph relationships include:

* `Country → HAS_NEED → MentalHealthNeed`
* `WellbeingProgram → ADDRESSES → MentalHealthNeed`
* `Country → HAS_SURVEY_DATA → SurveySnapshot`
* `Country → HAS_WHO_PROFILE → WHOProfile`
* `Country → HAS_FACILITY → Facility`
* `WellbeingProgram → EVIDENCED_BY → GovDataset`
* `Company → LOCATED_IN → Country`

These relationships allow the system to identify which programs best address the needs present in each country, and to connect registered employers to their regional context. :contentReference[oaicite:6]{index=6} :contentReference[oaicite:7]{index=7}

---

# Database Integration

The application integrates relational and graph databases to combine statistical analysis with relationship-based recommendations.

### Workflow

1. Survey data is stored and processed in PostgreSQL.
2. SQL views compute aggregated country-level metrics.
3. A data loader script extracts these aggregates.
4. Aggregates are converted into graph nodes and relationships in Neo4j.
5. The graph model connects mental health needs with recommended programs.
6. The FastAPI backend queries PostgreSQL for analytics and Neo4j for recommendations and graph traversal. :contentReference[oaicite:8]{index=8}

### Example Use Case

When a company requests recommendations for a specific country:

1. The system queries PostgreSQL to retrieve country-level workplace mental health metrics.
2. Identified needs are mapped to graph relationships in Neo4j.
3. The graph identifies programs that address those needs.
4. Programs are ranked by need coverage.
5. The API returns recommended workplace wellness initiatives along with WHO context and selected country-level statistics. :contentReference[oaicite:9]{index=9} :contentReference[oaicite:10]{index=10}

---

# API Architecture

BridgeWell uses a **FastAPI application** as the backend service layer. The API includes:

* **Health and status checking**
* **Country listing**
* **Country-level analysis from PostgreSQL**
* **Program recommendations from Neo4j**
* **Graph export data for visualization**
* **Company registration with tailored recommendations**

The API is initialized with a lifespan handler that closes PostgreSQL and Neo4j connections when the application shuts down. It also enables CORS for all origins, methods, and headers to simplify frontend development and integration. :contentReference[oaicite:11]{index=11}

---

# Connection Management

BridgeWell uses a shared database utility module for both PostgreSQL and Neo4j.

### PostgreSQL

The PostgreSQL connection is managed through helper functions that:

* reuse a global connection when available
* automatically reconnect if the connection is closed
* use `RealDictCursor` so query results behave like dictionaries
* commit transactions on success
* rollback on failure

### Neo4j

The Neo4j connection layer:

* initializes a reusable driver from environment variables
* creates sessions for Cypher execution
* returns query results as dictionaries

Both connections are closed cleanly by `close_connections()` during FastAPI shutdown. :contentReference[oaicite:12]{index=12}

---

# Running the Application

### Requirements

* Python 3.9+
* PostgreSQL
* Neo4j
* FastAPI

---

### Install Dependencies

```bash
pip install fastapi uvicorn psycopg2-binary neo4j python-dotenv requests
