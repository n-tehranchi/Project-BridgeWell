"""
sql/load_data.py
================
Loads mental_health.csv into the 4 PostgreSQL tables.
"""

import csv
import os
import sys
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", 5432),
        dbname=os.getenv("PG_DB", "bridgewell"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", ""),
    )


def to_bool(val):
    if val is None or val.strip() == "":
        return None
    return val.strip() in ("1", "True", "true", "yes", "Yes")


def to_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def load(csv_path: str, batch_size: int = 250):
    print(f"Reading {csv_path}...")
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"  {len(rows):,} rows loaded into memory")

    conn = get_connection()
    cur = conn.cursor()

    print("Inserting respondents...")
    respondent_sql = """
        INSERT INTO respondents
            (age, gender, country, education, marital_status, income_level,
             family_history_mental_illness, trauma_history,
             close_friend_count, social_support)
        VALUES %s
        RETURNING respondent_id
    """
    respondent_ids = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        values = [
            (
                to_int(r["Age"]),
                r["Gender"],
                r["Country"],
                r["Education"],
                r["Marital_Status"],
                r["Income_Level"],
                to_bool(r["Family_History_Mental_Illness"]),
                to_bool(r["Trauma_History"]),
                to_int(r["Close_Friends_Count"]),
                to_int(r["Social_Support"]),
            )
            for r in batch
        ]
        result = psycopg2.extras.execute_values(cur, respondent_sql, values, fetch=True)
        respondent_ids.extend(rid[0] for rid in result)
        conn.commit()
        print(f"  respondents: {min(i+batch_size, len(rows)):,}/{len(rows):,}", end="\r")
    print(f"  respondents: {len(respondent_ids):,} inserted          ")

    print("Inserting work_profiles...")
    work_sql = """
        INSERT INTO work_profiles
            (respondent_id, employment_status, work_hours_per_week, remote_work,
             job_satisfaction, work_stress_level, work_life_balance,
             ever_bullied_at_work, company_mental_health_support, financial_stress)
        VALUES %s
    """
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        ids_batch = respondent_ids[i : i + batch_size]
        values = [
            (
                rid,
                r["Employment_Status"],
                to_float(r["Work_Hours_Per_Week"]),
                r["Remote_Work"],
                to_int(r["Job_Satisfaction"]),
                to_int(r["Work_Stress_Level"]),
                to_int(r["Work_Life_Balance"]),
                to_bool(r["Ever_Bullied_At_Work"]),
                r["Company_Mental_Health_Support"],
                to_int(r["Financial_Stress"]),
            )
            for r, rid in zip(batch, ids_batch)
        ]
        psycopg2.extras.execute_values(cur, work_sql, values)
        conn.commit()
        print(f"  work_profiles: {min(i+batch_size, len(rows)):,}/{len(rows):,}", end="\r")
    print(f"  work_profiles: {len(rows):,} inserted          ")

    print("Inserting lifestyle_factors...")
    lifestyle_sql = """
        INSERT INTO lifestyle_factors
            (respondent_id, exercise_per_week, sleep_hours_per_night, caffeine_drinks_per_day,
             alcohol_frequency, smoking, screen_time_hours_day,
             social_media_hours_day, hobby_time_hours_week, diet_quality)
        VALUES %s
    """
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        ids_batch = respondent_ids[i : i + batch_size]
        values = [
            (
                rid,
                r["Exercise_Per_Week"],
                to_float(r["Sleep_Hours_Night"]),
                to_int(r["Caffeine_Drinks_Day"]),
                r["Alcohol_Frequency"],
                r["Smoking"],
                to_float(r["Screen_Time_Hours_Day"]),
                to_float(r["Social_Media_Hours_Day"]),
                to_float(r["Hobby_Time_Hours_Week"]),
                r["Diet_Quality"],
            )
            for r, rid in zip(batch, ids_batch)
        ]
        psycopg2.extras.execute_values(cur, lifestyle_sql, values)
        conn.commit()
        print(f"  lifestyle_factors: {min(i+batch_size, len(rows)):,}/{len(rows):,}", end="\r")
    print(f"  lifestyle_factors: {len(rows):,} inserted          ")

    print("Inserting mental_health_status...")
    mhs_sql = """
        INSERT INTO mental_health_status
            (respondent_id, feeling_sad_down, loss_of_interest, sleep_trouble,
             fatigue, poor_appetite_or_overeating, feeling_worthless,
             concentration_difficulty, anxious_nervous, panic_attacks,
             mood_swings, irritability, obsessive_thoughts, compulsive_behavior,
             self_harm_thoughts, suicidal_thoughts, loneliness, feel_understood,
             discuss_mental_health, previously_diagnosed, ever_sought_treatment,
             on_therapy_now, on_medication, has_mental_health_issue)
        VALUES %s
    """
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        ids_batch = respondent_ids[i : i + batch_size]
        values = [
            (
                rid,
                to_int(r["Feeling_Sad_Down"]),
                to_int(r["Loss_Of_Interest"]),
                to_int(r["Sleep_Trouble"]),
                to_int(r["Fatigue"]),
                to_int(r["Poor_Appetite_Or_Overeating"]),
                to_int(r["Feeling_Worthless"]),
                to_int(r["Concentration_Difficulty"]),
                to_int(r["Anxious_Nervous"]),
                to_int(r["Panic_Attacks"]),
                to_int(r["Mood_Swings"]),
                to_int(r["Irritability"]),
                to_int(r["Obsessive_Thoughts"]),
                to_int(r["Compulsive_Behavior"]),
                to_int(r["Self_Harm_Thoughts"]),
                to_int(r["Suicidal_Thoughts"]),
                to_int(r["Loneliness"]),
                to_int(r["Feel_Understood"]),
                r["Discuss_Mental_Health"],
                to_bool(r["Previously_Diagnosed"]),
                to_bool(r["Ever_Sought_Treatment"]),
                to_bool(r["On_Therapy_Now"]),
                to_bool(r["On_Medication"]),
                to_bool(r["Has_Mental_Health_Issue"]),
            )
            for r, rid in zip(batch, ids_batch)
        ]
        psycopg2.extras.execute_values(cur, mhs_sql, values)
        conn.commit()
        print(f"  mental_health_status: {min(i+batch_size, len(rows)):,}/{len(rows):,}", end="\r")
    print(f"  mental_health_status: {len(rows):,} inserted          ")

    cur.close()
    conn.close()
    print("\n All data loaded successfully.")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/mental_health.csv"
    load(csv_path)