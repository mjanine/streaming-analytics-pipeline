# Enterprise Streaming Analytics & Data Warehouse Pipeline

## 📌 Overview
An end-to-end data engineering and analytics solution designed for a digital streaming platform. The pipeline ingests unstructured catalog records from the Netflix Kaggle dataset alongside synthetic user activity and subscription logs, transforming them into a relational OLAP data warehouse. Advanced SQL window functions generate actionable insights on user retention, content engagement, and attributed revenue.

## 🛠 Tech Stack
* **Language:** Python 3.x, SQL
* **Data Engineering & ETL:** pandas, Regular Expressions (`re`)
* **Data Warehousing:** SQLite (`warehouse.db`)
* **Analytics & OLAP:** SQL Window Functions (`LAG`, `DENSE_RANK`), Date functions (ISO-8601)

## ⚡ Core Architecture & Pipeline Workflow

### 1. Extraction & Cleaning (`etl_pipeline.py`)
* Ingests 8,807 catalog items from `netflix_titles.csv`.
* Regular Expression (`re`) parsing standardizes malformed duration values into numerical quantities (`duration_num`) and units (`duration_unit`).
* Imputes missing numeric durations using content-type median values (90 mins for Movies; 1 season for TV Shows).
* Standardizes dates into ISO-8601 (`YYYY-MM-DD`) format.

### 2. Relational Warehouse Schema (`warehouse.db`)
* **`content_catalog` (Dimension Table):** Primary key `show_id`, content classification, duration attributes, and release metadata.
* **`user_subscriptions` (Dimension Table):** Primary key `user_id`, tier plan levels (Basic, Standard, Premium), monthly billing, and auto-renew status flags.
* **`watch_logs` (Fact Table):** Primary key `log_id`, foreign keys to catalog and subscribers, watch dates, session durations, and completion percentages.

### 3. OLAP Analytics (`olap_analysis.py`)
* **User Viewing Streaks (`LAG`):** Calculates chronological gaps between consecutive streaming events to isolate user viewing habituation and streak length (identifying high-engagement cohorts with up to 4-day streaks).
* **Genre Revenue & Engagement Ranking (`DENSE_RANK`):** Unnests comma-separated content categories and ranks genres across total watch duration and attributed monthly revenue (identifying Dramas and Comedies as top retention anchors).

## 📊 Key Findings
* **Catalog Mix:** 8,807 total titles (69.6% Movies, 30.4% TV Shows).
* **Top Revenue & Engagement:** Dramas and Comedies consistently ranked #1 and #2 in total watch minutes and attributed subscription revenue.
* **Niche Engagement:** Documentaries and International TV Shows maintained high completion percentages despite smaller absolute catalog footprints.

## 🚀 How to Run

1. Clone repository and install dependencies:
   ```bash
   pip install -r requirements.txt