from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from app.auth import get_current_user, COOKIE_NAME
from app.database import get_db_connection
from app.cv_engine import analyze_strip_image
from app.services.recommendation import get_recommendations
from datetime import datetime
import os
import shutil

router = APIRouter()

@router.post("/users/onboard")
async def onboard_user(
    language_pref: str = Form(...),
    region: str = Form(...),
    user=Depends(get_current_user)
):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET language_pref = ?, region = ? WHERE id = ?",
            (language_pref, region, user["id"])
        )
        conn.commit()
    except Exception as e:
        print(f"Onboarding update failed: {e}")
        raise HTTPException(status_code=500, detail="Database write failure")
    finally:
        conn.close()

    # Redirect to home, which will redirect to farmer
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/scans/analyze")
async def analyze_scan(
    file: UploadFile = File(...),
    region: str = Form("General"),
    user=Depends(get_current_user)
):
    # Determine user id
    user_id = user["id"] if user else 1 # Default to guest/first user
    user_region = user["region"] if user else region

    # Ensure uploads folder exists
    os.makedirs("uploads", exist_ok=True)
    
    # Save file to disk
    file_path = f"uploads/{datetime.utcnow().timestamp()}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Run OpenCV analysis
        results = analyze_strip_image(file_path)
        
        # Fetch consolidated recommendations (CCI + Regional)
        rec_data = get_recommendations(results["cci_score"], user_region)
        
        # Save scan in database
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO scans (
                user_id, fi_score, vi_score, cci_score, euclidean_distance, 
                risk_level, confidence, timestamp, trend, 
                indicator1_rgb, indicator2_rgb, recommendations, image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, 
            results["fi_score"], 
            results["vi_score"], 
            results["cci_score"], 
            results["euclidean_distance"],
            rec_data["risk_level"], 
            results["confidence"], 
            now, 
            results["trend"],
            str(results["ind1_rgb"]), 
            str(results["ind2_rgb"]), 
            rec_data["combined_advice"], 
            file_path
        ))
        conn.commit()
        conn.close()
        
        # Assemble response
        payload = {
            **results,
            "recommendations": rec_data["combined_advice"],
            "timestamp": now,
            "sync_status": "Synced"
        }
        return JSONResponse(content=payload)
        
    except Exception as e:
        print(f"Error during scan analysis: {e}")
        # Clean up file in case of error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scans/demo-scan")
async def demo_scan(
    level: str = "caution",
    region: str = "General",
    user=Depends(get_current_user)
):
    """
    Runs full OpenCV color pipeline against a pre-generated testing strip.
    Allows complete frontend demo flow without file uploads.
    """
    user_id = user["id"] if user else 1
    user_region = user["region"] if user else region
    
    # Map level to pre-generated assets
    sample_file = f"static/images/sample_strip_{level}.png"
    if not os.path.exists(sample_file):
        sample_file = "static/images/sample_strip.png" # Fallback

    try:
        # Run standard OpenCV pipeline
        results = analyze_strip_image(sample_file)
        
        # Fetch recommendations
        rec_data = get_recommendations(results["cci_score"], user_region)
        
        # Save scan in database
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO scans (
                user_id, fi_score, vi_score, cci_score, euclidean_distance, 
                risk_level, confidence, timestamp, trend, 
                indicator1_rgb, indicator2_rgb, recommendations, image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, 
            results["fi_score"], 
            results["vi_score"], 
            results["cci_score"], 
            results["euclidean_distance"],
            rec_data["risk_level"], 
            results["confidence"], 
            now, 
            results["trend"],
            str(results["ind1_rgb"]), 
            str(results["ind2_rgb"]), 
            rec_data["combined_advice"], 
            sample_file
        ))
        conn.commit()
        conn.close()
        
        payload = {
            **results,
            "recommendations": rec_data["combined_advice"],
            "timestamp": now,
            "sync_status": "Synced"
        }
        return JSONResponse(content=payload)
        
    except Exception as e:
        print(f"Error during demo scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
