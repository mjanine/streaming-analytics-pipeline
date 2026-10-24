import pandas as pd
import sqlite3
import re
import os
import logging
from datetime import datetime, timedelta
import numpy as np

# Configure logging to write to both stdout and milestone1_log.txt
LOG_FILE = "milestone1_log.txt"
DB_FILE = "warehouse.db"
CSV_FILE = "netflix_titles.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler()
    ]
)

def clean_duration(val):
    """Extract numeric duration and unit (minutes vs seasons)."""
    if pd.isna(val) or not str(val).strip():
        return None, None
    val_str = str(val).strip()
    match = re.search(r'(\d+)\s*(min|Season|Seasons)?', val_str, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        unit = match.group(2).capitalize() if match.group(2) else ("Min" if num > 10 else "Season")
        return num, unit
    return None, None

def run_etl():
    logging.info("Starting Milestone 1 ETL Pipeline Execution.")

    if not os.path.exists(CSV_FILE):
        logging.error(f"Input file '{CSV_FILE}' not found. Please place it in the working directory.")
        return

    # Step 1: Ingest & Clean Netflix Catalog Data
    logging.info(f"Ingesting catalog data from '{CSV_FILE}'...")
    df = pd.read_csv(CSV_FILE)
    initial_count = len(df)
    logging.info(f"Loaded {initial_count} records from dataset.")

    # Clean malformed/missing duration strings
    dur_cleaned = df['duration'].apply(clean_duration)
    df['duration_num'] = [x[0] for x in dur_cleaned]
    df['duration_unit'] = [x[1] for x in dur_cleaned]

    # Fill default numeric durations where missing based on content type
    movie_median = df[df['type'] == 'Movie']['duration_num'].median() or 90
    tv_median = df[df['type'] == 'TV Show']['duration_num'].median() or 1
    
    df.loc[(df['type'] == 'Movie') & (df['duration_num'].isna()), 'duration_num'] = movie_median
    df.loc[(df['type'] == 'Movie') & (df['duration_unit'].isna()), 'duration_unit'] = 'Min'
    df.loc[(df['type'] == 'TV Show') & (df['duration_num'].isna()), 'duration_num'] = tv_median
    df.loc[(df['type'] == 'TV Show') & (df['duration_unit'].isna()), 'duration_unit'] = 'Season'

    # Standardize date_added
    df['date_added'] = pd.to_datetime(df['date_added'].str.strip(), errors='coerce').dt.strftime('%Y-%m-%d')

    logging.info(f"Duration cleaning completed. Null durations remaining: {df['duration_num'].isna().sum()}")

    # Step 2: Create SQLite Database & Schemas
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop existing tables to support idempotent re-runs
    cursor.executescript("""
        DROP TABLE IF EXISTS content_catalog;
        DROP TABLE IF EXISTS user_subscriptions;
        DROP TABLE IF EXISTS watch_logs;

        CREATE TABLE content_catalog (
            show_id TEXT PRIMARY KEY,
            type TEXT,
            title TEXT,
            director TEXT,
            cast TEXT,
            country TEXT,
            date_added TEXT,
            release_year INTEGER,
            rating TEXT,
            duration_raw TEXT,
            duration_num INTEGER,
            duration_unit TEXT,
            listed_in TEXT,
            description TEXT
        );

        CREATE TABLE user_subscriptions (
            user_id INTEGER PRIMARY KEY,
            signup_date TEXT,
            plan_type TEXT,
            monthly_fee REAL,
            auto_renew INTEGER,
            status TEXT
        );

        CREATE TABLE watch_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            show_id TEXT,
            watch_date TEXT,
            watch_duration_minutes INTEGER,
            completion_percentage REAL,
            FOREIGN KEY (user_id) REFERENCES user_subscriptions(user_id),
            FOREIGN KEY (show_id) REFERENCES content_catalog(show_id)
        );
    """)

    # Step 3: Load Content Catalog into SQLite
    catalog_records = df.rename(columns={'duration': 'duration_raw'})[[
        'show_id', 'type', 'title', 'director', 'cast', 'country',
        'date_added', 'release_year', 'rating', 'duration_raw',
        'duration_num', 'duration_unit', 'listed_in', 'description'
    ]]
    catalog_records.to_sql('content_catalog', conn, if_exists='append', index=False)
    logging.info(f"Loaded {len(catalog_records)} rows into table 'content_catalog'.")

    # Step 4: Generate Synthetic User Subscriptions & Watch History Logs (Warehouse Requirements)
    np.random.seed(42)
    num_users = 500
    plans = ['Basic', 'Standard', 'Premium']
    fees = {'Basic': 9.99, 'Standard': 15.49, 'Premium': 19.99}
    
    user_rows = []
    base_date = datetime(2025, 1, 1)
    for u_id in range(1001, 1001 + num_users):
        signup = base_date + timedelta(days=int(np.random.randint(0, 365)))
        plan = np.random.choice(plans, p=[0.3, 0.5, 0.2])
        renew = int(np.random.choice([0, 1], p=[0.2, 0.8]))
        status = 'Active' if renew else np.random.choice(['Cancelled', 'Expired'])
        user_rows.append((u_id, signup.strftime('%Y-%m-%d'), plan, fees[plan], renew, status))

    cursor.executemany("""
        INSERT INTO user_subscriptions (user_id, signup_date, plan_type, monthly_fee, auto_renew, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, user_rows)
    logging.info(f"Loaded {len(user_rows)} rows into table 'user_subscriptions'.")

    # Generate synthetic watch logs for window function analytics downstream
    show_ids = catalog_records['show_id'].values
    log_rows = []
    for _ in range(3000):
        u_id = int(np.random.randint(1001, 1001 + num_users))
        s_id = str(np.random.choice(show_ids))
        w_date = base_date + timedelta(days=int(np.random.randint(0, 450)))
        w_dur = int(np.random.randint(10, 180))
        comp = round(float(np.random.uniform(0.1, 1.0)), 2)
        log_rows.append((u_id, s_id, w_date.strftime('%Y-%m-%d'), w_dur, comp))

    cursor.executemany("""
        INSERT INTO watch_logs (user_id, show_id, watch_date, watch_duration_minutes, completion_percentage)
        VALUES (?, ?, ?, ?, ?)
    """, log_rows)
    logging.info(f"Loaded {len(log_rows)} rows into table 'watch_logs'.")

    conn.commit()
    conn.close()
    logging.info("ETL Pipeline completed successfully. SQLite DB generated: warehouse.db")

if __name__ == "__main__":
    run_etl()