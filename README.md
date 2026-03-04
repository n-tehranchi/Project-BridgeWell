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

The application combines **relational database analytics and graph-based recommendation modeling**. Survey data and structured workforce information are stored in PostgreSQL, while relationships between mental health needs, countries, programs, and resources are modeled using a Neo4j graph database. A FastAPI backend integrates these components and exposes endpoints for analysis and program recommendations.

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

* Mental health workforce statistics (e.g., psychiatrists per 100k population)
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

Aggregated SQL views support the analysis API endpoints:

Examples include:

* **employer_gap_by_country**
* **lifestyle_risk_by_country**
* **treatment_gap_by_country**

These views calculate metrics such as:

* average stress level
* work-life balance scores
* percentage of respondents lacking employer support
* untreated mental health rates

These aggregated metrics feed into the graph model.

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
* Anxiety & depression support
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

---

### Relationships

Key graph relationships include:

* `Country → HAS_NEED → MentalHealthNeed`
* `WellbeingProgram → ADDRESSES → MentalHealthNeed`
* `Country → HAS_SURVEY_DATA → SurveySnapshot`
* `Country → HAS_WHO_PROFILE → WHOProfile`
* `Country → HAS_FACILITY → Facility`
* `WellbeingProgram → EVIDENCED_BY → GovDataset`

These relationships allow the system to identify which programs best address the needs present in each country.

---

# Database Integration

The application integrates relational and graph databases to combine statistical analysis with relationship-based recommendations.

### Workflow

1. Survey data is stored and processed in PostgreSQL.
2. SQL views compute aggregated country-level metrics.
3. A data loader script extracts these aggregates.
4. Aggregates are converted into graph nodes and relationships in Neo4j.
5. The graph model connects mental health needs with recommended programs.

### Example Use Case

When a company requests recommendations for a specific country:

1. The system queries PostgreSQL to analyze mental health risk indicators.
2. Identified needs are mapped to graph nodes in Neo4j.
3. The graph identifies programs that address those needs.
4. Programs are ranked by how many needs they address.
5. The system returns recommended workplace wellness initiatives.

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
```

---

### Environment Variables

Create a `.env` file with database credentials:

```
PG_HOST=localhost
PG_PORT=5432
PG_DB=bridgewell
PG_USER=postgres
PG_PASSWORD=password

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

### Load Graph Data

Run the graph loader to populate Neo4j:

```bash
python load_graph.py
```

This script:

* Imports survey aggregates
* Loads WHO indicators
* Retrieves facility data from OpenStreetMap
* Retrieves wellness datasets from data.gov
* Seeds wellbeing program nodes

---

### Run the API

Start the FastAPI application:

```bash
uvicorn main:app --reload
```

---

### API Endpoints

**Health Check**

```
GET /
```

**List Countries**

```
GET /countries
```

**Country Analysis**

```
GET /analysis/{country}
```

**Program Recommendations**

```
GET /recommendations/{country}
```

**Graph Visualization Data**

```
GET /graph/{country}
```

**Register Company**

```
POST /company
```
