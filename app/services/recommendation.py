from app.database import get_db_connection
from typing import Dict, Any, List

def get_recommendations(cci_score: float, region: str) -> Dict[str, Any]:
    """
    Combines CCI-based general recommendations with region-specific recommendations
    queried from the SQLite database.
    """
    # 1. Determine Risk Level and General Recommendation
    if cci_score <= 20:
        risk_level = "Safe"
        general_rec = "Fungal contamination is minimal. Continue storage under standard hermetic conditions."
    elif cci_score <= 40:
        risk_level = "Monitor"
        general_rec = "Minor microbial activity detected. Reinspect the grain pile and scan again in 48 hours."
    elif cci_score <= 60:
        risk_level = "Caution"
        general_rec = "Elevated fungal index. Improve ventilation and run dynamic aeration systems to reduce humidity."
    elif cci_score <= 80:
        risk_level = "High Risk"
        general_rec = "High contamination risk. Quarantine the affected grain bags immediately and isolate the storage bin."
    else:
        risk_level = "Critical"
        general_rec = "Critical mycotoxin danger. Immediate laboratory testing required before distribution. Terminate raw food usage."

    # 2. Query regional recommendations from database
    regional_recs: List[str] = []
    primary_pathogen = "General"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Search for exact matches on region and risk_level
        cursor.execute(
            "SELECT fungus_type, recommendation FROM regional_recommendations WHERE region = ? AND risk_level = ?",
            (region, risk_level)
        )
        rows = cursor.fetchall()
        for row in rows:
            primary_pathogen = row["fungus_type"]
            regional_recs.append(f"[{row['fungus_type']} Guideline]: {row['recommendation']}")
            
        # If no specific regional recommendation exists, pull general guidelines
        if not regional_recs:
            cursor.execute(
                "SELECT fungus_type, recommendation FROM regional_recommendations WHERE region = 'General' AND risk_level = ?",
                (risk_level,)
            )
            row = cursor.fetchone()
            if row:
                regional_recs.append(row["recommendation"])
    except Exception as e:
        print(f"Error querying regional recommendations: {e}")
    finally:
        conn.close()

    # Formulate final advice
    action_items = [general_rec]
    action_items.extend(regional_recs)

    return {
        "risk_level": risk_level,
        "primary_recommendation": general_rec,
        "regional_guidelines": regional_recs,
        "combined_advice": " ".join(action_items),
        "primary_pathogen": primary_pathogen,
        "action_list": action_items
    }
