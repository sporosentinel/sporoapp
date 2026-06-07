import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        region TEXT,
        language_pref TEXT DEFAULT 'en',
        created_at TEXT NOT NULL
    )
    """)

    # 2. Scans Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        fi_score REAL NOT NULL,
        vi_score REAL NOT NULL,
        cci_score REAL NOT NULL,
        euclidean_distance REAL NOT NULL,
        risk_level TEXT NOT NULL,
        confidence REAL NOT NULL,
        timestamp TEXT NOT NULL,
        trend TEXT NOT NULL,
        indicator1_rgb TEXT NOT NULL,
        indicator2_rgb TEXT NOT NULL,
        recommendations TEXT NOT NULL,
        image_path TEXT,
        sync_status TEXT DEFAULT 'synced',
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # 3. Map Metadata Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS map_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_name TEXT UNIQUE NOT NULL,
        file_path TEXT NOT NULL,
        downloaded_at TEXT NOT NULL,
        version TEXT NOT NULL
    )
    """)

    # 4. Cached Intelligence Table (Local risk overlays and reports)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cached_intelligence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_id TEXT UNIQUE NOT NULL,
        region_name TEXT NOT NULL,
        risk_score REAL NOT NULL,
        mycotoxin_level TEXT NOT NULL,
        details TEXT,
        updated_at TEXT NOT NULL
    )
    """)

    # 5. Regional Recommendations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regional_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region TEXT NOT NULL,
        fungus_type TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(region, fungus_type, risk_level)
    )
    """)

    conn.commit()

    # Seed Default Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        # Admin User
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, region, language_pref, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("admin", hash_password("admin123"), "admin", "Global", "en", now)
        )
        # Farmer User (High-humidity Coastal region)
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, region, language_pref, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("farmer", hash_password("farmer123"), "farmer", "High-humidity Coastal", "en", now)
        )
        # Another Farmer User (Aspergillus-prone South region)
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, region, language_pref, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("south_farmer", hash_password("farmer123"), "farmer", "Aspergillus-prone South", "en", now)
        )
        conn.commit()

    # Seed Default Regional Recommendations
    cursor.execute("SELECT COUNT(*) FROM regional_recommendations")
    if cursor.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        recommendations = [
            ("High-humidity Coastal", "Aspergillus flavus", "Caution", "Elevated local humidity detected. Enhance bin aeration; check grain moisture levels twice daily.", now),
            ("High-humidity Coastal", "Penicillium verrucosum", "High Risk", "High Penicillium risk in damp coastal regions. Quarantine grain immediately and run low-heat dryers.", now),
            ("Aspergillus-prone South", "Aspergillus flavus", "Critical", "Critical risk alert: Aspergillus outbreaks are high in Southern soils. Sample storage units immediately for aflatoxin.", now),
            ("Aspergillus-prone South", "Fusarium graminearum", "Monitor", "Fusarium spores detected locally. Maintain storage temperatures below 15°C to arrest development.", now),
            ("General", "Generic", "Safe", "Fungal levels are within safe storage parameters. Maintain standard hermetic sealing.", now),
            ("General", "Generic", "Monitor", "Slight temperature delta detected. Increase checking frequency to every 48 hours.", now),
            ("General", "Generic", "Caution", "Elevated moisture indices. Activate ventilation systems to reduce relative humidity.", now),
            ("General", "Generic", "High Risk", "High contamination risk. Separate affected bags, verify seal integrity, and quarantine.", now),
            ("General", "Generic", "Critical", "Active sporulation detected. Immediate testing required. Apply protective fungicides or clear the storage bin.", now)
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO regional_recommendations (region, fungus_type, risk_level, recommendation, updated_at) VALUES (?, ?, ?, ?, ?)",
            recommendations
        )
        conn.commit()

    # Seed Mock Map Metadata & Cached Intelligence
    cursor.execute("SELECT COUNT(*) FROM cached_intelligence")
    if cursor.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        intelligence_data = [
            ("region_1", "High-humidity Coastal", 68.5, "0.15 ppm", "Coastal warm winds have increased spore germination rates.", now),
            ("region_2", "Aspergillus-prone South", 84.2, "0.45 ppm", "Soil-borne heatwave triggered active aflatoxin development.", now),
            ("region_3", "Northern Grain Belt", 12.0, "0.02 ppm", "Cool temperatures and low humidity keep fungal growth low.", now),
            ("region_4", "Western Drylands", 34.0, "0.08 ppm", "Moderate risk in poorly ventilated silos.", now)
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO cached_intelligence (region_id, region_name, risk_score, mycotoxin_level, details, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            intelligence_data
        )
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
