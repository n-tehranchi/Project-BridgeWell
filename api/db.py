"""
api/db.py
=========
Connection managment for PostgreSQL & Neo4j
"""

import os
import psycopg2
import psycopg2.extras
from neo4j import GraphDatabase
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

#postgreSQL connection

_pg_conn = None

def get_pg_connection():
    global _pg_conn
    try:
        if _pg_conn is None or _pg_conn.closed:
            raise psycopg2.OperationalError("No connection")
        _pg_conn.cursor().execute("SELECT 1")
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        _pg_conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", 5432)),
            dbname=os.getenv("PG_DB", "mindbridge"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", ""),
        )
    return _pg_conn

@contextmanager
def pg_cursor():
    conn = get_pg_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try: 
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

def pg_query(sql: str, params=None) -> list:
    with pg_cursor() as cur:
        cur.execute(sql, params or ())
        return [dict(row) for row in cur.fetchall()]
    
#neo4j connection
_neo4j_driver = None
def get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI",     "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "password"),
            ),
        )
    return _neo4j_driver

def neo4j_query(cypher: str, params: dict = None) -> list:
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]
    
def close_connections():
    global _pg_conn, _neo4j_driver
    if _pg_conn and not _pg_conn.closed:
        _pg_conn.close()
    if _neo4j_driver:
        _neo4j_driver.close()