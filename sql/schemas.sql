-- ==================================================
-- SQL SCHEMA
-- ==================================================
-- --------------------------------------------------
-- RESPONDENTS - one row per participant 
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS respondents (
    respondent_id       SERIAL PRIMARY KEY,
    age                 INTEGER NOT NULL, 
    gender              VARCHAR(30),
    country             VARCHAR(100) NOT NULL, 
    education           VARCHAR(50),
    marital_status      VARCHAR(30), 
    income_level        VARCHAR(20),
    family_history_mental_illness   BOOLEAN,
    trauma_history      BOOLEAN,
    close_friend_count  INTEGER,
    social_support      INTEGER
);

-- --------------------------------------------------
-- WORK PROFILES - one row per respondent
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS work_profiles (
    work_profile_id         SERIAL PRIMARY KEY,
    respondent_id           INTEGER NOT NULL REFERENCES respondents(respondent_id) ON DELETE CASCADE,
    employment_status       VARCHAR(30),
    work_hours_per_week     FLOAT,
    remote_work             VARCHAR(10),
    job_satisfaction        INTEGER,
    work_stress_level       INTEGER,
    work_life_balance       INTEGER,
    ever_bullied_at_work    BOOLEAN,
    company_mental_health_support VARCHAR(20),
    financial_stress        INTEGER
);

-- --------------------------------------------------
-- LIFESTYLE - one row per respondent
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS lifestyle_factors(
    lifestyle_id            SERIAL PRIMARY KEY,
    respondent_id           INTEGER NOT NULL REFERENCES respondents(respondent_id) ON DELETE CASCADE,
    exercise_per_week       VARCHAR(20),
    sleep_hours_per_night   FLOAT,
    caffeine_drinks_per_day INTEGER,
    alcohol_frequency       VARCHAR(20),
    smoking                 VARCHAR(20),
    screen_time_hours_day   FLOAT,
    social_media_hours_day  FLOAT,
    hobby_time_hours_week   FLOAT,
    diet_quality            VARCHAR(20)
);

-- --------------------------------------------------
-- MENTAL STATUS - one row per respondent
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS mental_health_status(
    status_id               SERIAL PRIMARY KEY,
    respondent_id           INTEGER NOT NULL REFERENCES respondents(respondent_id) ON DELETE CASCADE,

    --symptom severity scores
    feeling_sad_down            INTEGER,
    loss_of_interest            INTEGER,
    sleep_trouble               INTEGER,
    fatigue                     INTEGER,
    poor_appetite_or_overeating INTEGER,
    feeling_worthless           INTEGER,
    concentration_difficulty    INTEGER,
    anxious_nervous             INTEGER,
    panic_attacks               INTEGER,
    mood_swings                 INTEGER,
    irritability                INTEGER,
    obsessive_thoughts          INTEGER,
    compulsive_behavior         INTEGER,
    self_harm_thoughts          INTEGER,
    suicidal_thoughts           INTEGER,

    --psychosocial context
    loneliness                  INTEGER,
    feel_understood             INTEGER,
    discuss_mental_health       VARCHAR(30),

    --diagnoisis & treatment flags
    previously_diagnosed        BOOLEAN,
    ever_sought_treatment       BOOLEAN,
    on_therapy_now              BOOLEAN,
    on_medication               BOOLEAN,
    has_mental_health_issue     BOOLEAN,

    --score
    composite_symptom_score     FLOAT GENERATED ALWAYS AS(
        (feeling_sad_down + loss_of_interest + sleep_trouble + fatigue +
        poor_appetite_or_overeating + feeling_worthless + concentration_difficulty +
        anxious_nervous + panic_attacks + mood_swings + irritability +
        obsessive_thoughts + compulsive_behavior + self_harm_thoughts + 
        suicidal_thoughts)::FLOAT / 15.0
    ) STORED
);

-- ==================================================
-- VIEWS for API layer
-- ==================================================

-- employer gas analysis by company 
CREATE OR REPLACE VIEW employer_gap_by_country AS
SELECT
    r.country, 
    COUNT(*)                                        AS total_respondents,
    ROUND(AVG(wp.work_stress_level)::NUMERIC, 2)    AS avg_stress,
    ROUND(AVG(wp.work_life_balance)::NUMERIC, 2)    AS avg_work_life_balance,
    ROUND(AVG(wp.job_satisfaction)::NUMERIC, 2)     AS avg_job_satisfaction,
    ROUND(AVG(mhs.composite_symptom_score)::NUMERIC, 2) AS avg_symptom_score,
    SUM(CASE WHEN wp.company_mental_health_support = 'No'   THEN 1 ELSE 0 END) AS count_no_support,
    SUM(CASE WHEN wp.company_mental_health_support = 'Not sure' THEN 1 ELSE 0 END) AS count_unsure, 
    ROUND((
        100.0 * SUM(CASE WHEN wp.company_mental_health_support IN ('No', 'Not sure') THEN 1 ELSE 0 END)
        / COUNT(*)
    )::NUMERIC, 1) AS pct_lacking_support
FROM respondents r
JOIN work_profiles wp ON r.respondent_id = wp.respondent_id
JOIN mental_health_status mhs ON r.respondent_id = mhs.respondent_id
GROUP BY r.country
ORDER BY avg_symptom_score DESC;

-- lifestyle risk profile by country
CREATE OR REPLACE VIEW lifestyle_risk_by_country AS 
SELECT 
    r.country, 
    ROUND(AVG(lf.sleep_hours_per_night)::NUMERIC, 2)    AS avg_sleep_hours,
    ROUND(AVG(lf.screen_time_hours_day)::NUMERIC, 2)    AS avg_screen_time,
    ROUND(AVG(lf.caffeine_drinks_per_day)::NUMERIC, 2)  AS caffeine, 
    SUM(CASE WHEN lf.exercise_per_week = 'Never'        THEN 1 ELSE 0 END) AS count_no_exercise,
    SUM(CASE WHEN lf.diet_quality       IN('Poor', 'Average') THEN 1 ELSE 0 END) AS count_poor_diet,
    SUM(CASE WHEN lf.smoking           = 'Current'      THEN 1 ELSE 0 END) AS count_smokers, 
    SUM(CASE WHEN lf.alcohol_frequency  IN('Weekly', 'Daily') THEN 1 ELSE 0 END) AS count_freq_drinkers
FROM respondents r
JOIN lifestyle_factors lf ON r.respondent_id = lf.respondent_id
GROUP BY r.country
ORDER BY avg_sleep_hours ASC;

-- treatment gaps
CREATE OR REPLACE VIEW treatment_gap_by_country AS
SELECT
    r.country, 
    COUNT(*) FILTER (WHERE mhs.previously_diagnosed = TRUE) AS diagnosed_count,
    COUNT(*) FILTER (WHERE mhs.previously_diagnosed = TRUE
                        AND mhs.on_therapy_now = FALSE 
                        AND mhs.on_medication  = FALSE)     AS untreated_count,
    ROUND((
        100.0
        * COUNT(*) FILTER (WHERE mhs.previously_diagnosed = TRUE
                        AND mhs.on_therapy_now = FALSE 
                        AND mhs.on_medication  = FALSE)
        / NULLIF(COUNT(*) FILTER (WHERE mhs.previously_diagnosed = TRUE), 0)
    )::NUMERIC, 1)                                          AS pct_untreated
FROM respondents r
JOIN mental_health_status mhs ON r.respondent_id = mhs.respondent_id
GROUP BY r.country;

-- ==================================================
-- INDEXES
-- ==================================================
CREATE INDEX IF NOT EXISTS idx_respondents_country ON respondents(country);
CREATE INDEX IF NOT EXISTS idx_wp_support          ON work_profiles(company_mental_health_support);
CREATE INDEX IF NOT EXISTS idx_wp_respondent       ON work_profiles(respondent_id);
CREATE INDEX IF NOT EXISTS idx_lf_respondent       ON lifestyle_factors(respondent_id);