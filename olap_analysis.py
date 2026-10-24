import sqlite3
import pandas as pd
import sys

OUTPUT_FILE = "olap_output.txt"

class DualLogger:
    """Tee print output to both stdout and olap_output.txt"""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = DualLogger(OUTPUT_FILE)

def run_olap_queries():
    conn = sqlite3.connect("warehouse.db")

    print("==================================================================")
    print("       MILESTONE 2: OLAP ANALYTICS & WINDOW FUNCTION REPORT       ")
    print("==================================================================\n")

    # -------------------------------------------------------------------------
    # QUERY 1: User Viewing Streaks using Window Functions (LAG)
    # -------------------------------------------------------------------------
    print("--- 1. USER VIEWING STREAKS (WINDOW FUNCTION: LAG) ---")
    query_streaks = """
    WITH RankedLogs AS (
        SELECT DISTINCT
            user_id,
            watch_date
        FROM watch_logs
    ),
    DateDiffs AS (
        SELECT 
            user_id,
            watch_date,
            LAG(watch_date, 1) OVER (PARTITION BY user_id ORDER BY watch_date) as prev_watch_date,
            CAST(julianday(watch_date) - julianday(LAG(watch_date, 1) OVER (PARTITION BY user_id ORDER BY watch_date)) AS INTEGER) as days_since_prev
        FROM RankedLogs
    ),
    StreakGroups AS (
        SELECT 
            user_id,
            watch_date,
            SUM(CASE WHEN days_since_prev = 1 THEN 0 ELSE 1 END) OVER (PARTITION BY user_id ORDER BY watch_date) as streak_id
        FROM DateDiffs
    ),
    StreakLengths AS (
        SELECT 
            user_id,
            streak_id,
            COUNT(*) as streak_days,
            MIN(watch_date) as streak_start,
            MAX(watch_date) as streak_end
        FROM StreakGroups
        GROUP BY user_id, streak_id
    )
    SELECT 
        user_id,
        MAX(streak_days) as max_viewing_streak_days,
        MIN(streak_start) as earliest_streak_start,
        MAX(streak_end) as latest_streak_end
    FROM StreakLengths
    GROUP BY user_id
    ORDER BY max_viewing_streak_days DESC, user_id ASC
    LIMIT 10;
    """
    
    df_streaks = pd.read_sql_query(query_streaks, conn)
    print(df_streaks.to_string(index=False))
    print("\n" + "-"*65 + "\n")

    # -------------------------------------------------------------------------
    # QUERY 2: Top Genre Revenues & Watch Engagement using Window Functions (DENSE_RANK)
    # -------------------------------------------------------------------------
    print("--- 2. TOP GENRE REVENUES & ENGAGEMENT (WINDOW FUNCTION: DENSE_RANK) ---")
    query_genres = """
    WITH GenreSplits AS (
        SELECT 
            wl.log_id,
            wl.user_id,
            wl.watch_duration_minutes,
            us.monthly_fee,
            TRIM(g.value) as genre
        FROM watch_logs wl
        JOIN content_catalog cc ON wl.show_id = cc.show_id
        JOIN user_subscriptions us ON wl.user_id = us.user_id
        JOIN json_each('["' || REPLACE(cc.listed_in, ', ', '","') || '"]') g
    ),
    GenreAggregates AS (
        SELECT 
            genre,
            COUNT(DISTINCT user_id) as total_unique_viewers,
            SUM(watch_duration_minutes) as total_watch_minutes,
            ROUND(SUM(monthly_fee), 2) as estimated_attributed_revenue
        FROM GenreSplits
        GROUP BY genre
    )
    SELECT 
        genre,
        total_unique_viewers,
        total_watch_minutes,
        estimated_attributed_revenue,
        DENSE_RANK() OVER (ORDER BY estimated_attributed_revenue DESC) as revenue_rank,
        DENSE_RANK() OVER (ORDER BY total_watch_minutes DESC) as engagement_rank
    FROM GenreAggregates
    ORDER BY revenue_rank ASC
    LIMIT 10;
    """
    
    df_genres = pd.read_sql_query(query_genres, conn)
    print(df_genres.to_string(index=False))
    print("\n==================================================================")
    print("OLAP Analysis completed successfully. Log saved to 'olap_output.txt'")

    conn.close()

if __name__ == "__main__":
    run_olap_queries()