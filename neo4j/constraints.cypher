// ================================================
// MINDBRIDGE: NEO4J SCHEMA - CONSTRAINTS & INDEXES
// ================================================

// -- Uniqueness constraints 

// country is central hub
CREATE CONSTRAINT country_name_unique IF NOT EXISTS
    FOR (c:country) REQUIRE c.name IS UNIQUE;

// -- WHO profile 1:1 w/ country
CREATE CONSTRAINT who_profile_country_unique IF NOT EXISTS
    FOR (w:WHOProfile) REQUIRE w.country_name IS UNIQUE;

// Programs unique INDEXES
CREATE CONSTRAINT program_id_unique IF NOT EXISTS
    FOR (p:WellbeingProgram) REQUIRE p.program_id IS UNIQUE;

// Needs controlled vocab
CREATE CONSTRAINT need_name_unique IF NOT EXISTS
    FOR (n:MentalHealthNeed) REQUIRE n.name IS UNIQUE;

// Survey snapshots keyed by country
CREATE CONSTRAINT snapshot_country_unique IF NOT EXISTS
    FOR (s:SurveySnapshot) REQUIRE s.country IS UNIQUE;

//Companies with unique IDs
CREATE CONSTRAINT company_id_unique IF NOT EXISTS
    FOR (co:Company) REQUIRE co.company_id IS UNIQUE;

//OSM facilities with unique OSM IDs
CREATE CONSTRAINT facility_osm_unique IF NOT EXISTS
    FOR (f:Facility) REQUIRE f.osm_id IS UNIQUE;

//Government datasets from data.gov
CREATE CONSTRAINT dataset_id_unique IF NOT EXISTS
    FOR (d:GovDataset) REQUIRE d.identifier IS UNIQUE;

// --indexes for frequently queried properties -- 

// by type
CREATE INDEX program_type_idx IF NOT EXISTS
    FOR (p:WellbeingProgram) ON (p.program_type);

// filter facilities by category 
CREATE INDEX facility_category_idx IF NOT EXISTS
    FOR (f:Facility) ON (f.category);

// companies by industry 
CREATE INDEX company_industry_idx IF NOT EXISTS
    FOR (co:Company) ON (co.industry);

