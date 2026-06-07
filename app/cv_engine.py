import cv2
import numpy as np
import math
from typing import Tuple, Dict, Any

# Target/reference colors for calibration and indexing
# Indicator 1: Anthocyanin + NaHCO3 (Fungal Index)
# Healthy: #2E8B57 (46, 139, 87)
# Mild: #7A9E3A (122, 158, 58)
# Warning: #B56576 (181, 101, 118)
# Strong Positive: #E63946 (230, 57, 70)
IND1_HEALTHY = np.array([46, 139, 87], dtype=np.float32)
IND1_STRONG = np.array([230, 57, 70], dtype=np.float32)

# Indicator 2: VOC (VOC Index)
# Healthy: #6A0DAD (106, 13, 173)
# Mild: #8E44AD (142, 68, 173)
# Warning: #C44569 (196, 69, 105)
# Strong Positive: #FF4D6D (255, 77, 109)
IND2_HEALTHY = np.array([106, 13, 173], dtype=np.float32)
IND2_STRONG = np.array([255, 77, 109], dtype=np.float32)

# Standard calibrator reference patch target color (Light Gray)
REF_TARGET = np.array([224, 224, 224], dtype=np.float32)

def order_points(pts):
    """
    Orders 4 points: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def get_risk_level(cci: float) -> Tuple[str, float]:
    """
    Maps CCI score to category and returns confidence rating.
    0-20: Safe
    21-40: Monitor
    41-60: Caution
    61-80: High Risk
    81-100: Critical
    """
    if cci <= 20:
        return "Safe", round(95.0 - (cci * 0.25), 1)
    elif cci <= 40:
        return "Monitor", round(90.0 - ((cci - 20) * 0.3), 1)
    elif cci <= 60:
        return "Caution", round(88.0 - ((cci - 40) * 0.4), 1)
    elif cci <= 80:
        return "High Risk", round(92.0 - ((cci - 60) * 0.5), 1)
    else:
        return "Critical", round(96.0 - ((cci - 80) * 0.5), 1)

def analyze_strip_image(image_path: str) -> Dict[str, Any]:
    """
    Main OpenCV pipeline:
    1. Read image.
    2. Detect strip contour and apply perspective warp.
    3. Fallback to center-crop if contour fails.
    4. Extract RGB for reference, indicator 1 (FI), and indicator 2 (VI) zones.
    5. Perform lighting calibration using reference patch.
    6. Calculate FI, VI, Euclidean distances, and Combined Contamination Index (CCI).
    7. Formulate output payload.
    """
    # Read image in BGR, convert to RGB
    bgr_img = cv2.imread(image_path)
    if bgr_img is None:
        raise ValueError(f"Image could not be loaded from path: {image_path}")
    
    h, w, _ = bgr_img.shape
    aspect_ratio = w / h
    
    # Try finding strip contour
    warped = None
    detection_method = "contour_perspective_warp"
    
    # If the image itself has the aspect ratio of a test strip, skip contour detection.
    if 2.8 <= aspect_ratio <= 4.2:
        warped = cv2.resize(bgr_img, (400, 120))
        detection_method = "direct_strip_image"
    else:
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            # Strip contour must have 4 corners, cover at least 15% of the image, and match rectangular ratio
            if len(approx) == 4 and cv2.contourArea(c) > (h * w * 0.15):
                x, y, cw, ch = cv2.boundingRect(c)
                contour_aspect = cw / float(ch)
                if 2.5 <= contour_aspect <= 5.5:
                    pts = approx.reshape(4, 2)
                    rect = order_points(pts)
                    
                    # Target dimensions for warped strip: 400x120
                    dst_w, dst_h = 400, 120
                    dst = np.array([
                        [0, 0],
                        [dst_w - 1, 0],
                        [dst_w - 1, dst_h - 1],
                        [0, dst_h - 1]
                    ], dtype="float32")
                    
                    M = cv2.getPerspectiveTransform(rect, dst)
                    warped = cv2.warpPerspective(bgr_img, M, (dst_w, dst_h))
                    break

    # Fallback to center-cropping if detection failed
    if warped is None:
        # Take central rectangle representing a strip (aspect ratio 4:1)
        cy, cx = h // 2, w // 2
        crop_w = int(w * 0.7)
        crop_h = int(crop_w * 0.3)
        # Ensure we stay within boundaries
        y1 = max(0, cy - crop_h // 2)
        y2 = min(h, cy + crop_h // 2)
        x1 = max(0, cx - crop_w // 2)
        x2 = min(w, cx + crop_w // 2)
        
        cropped = bgr_img[y1:y2, x1:x2]
        warped = cv2.resize(cropped, (400, 120))
        detection_method = "center_crop_fallback"
    else:
        detection_method = "contour_perspective_warp"

    # Convert warped strip to RGB for color extraction
    warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
    
    # Crop ROIs for the three patches:
    # 1. Reference Calibrator: x from 30 to 70
    # 2. Indicator 1 (FI): x from 180 to 220
    # 3. Indicator 2 (VI): x from 310 to 350
    # y-range is standard [40, 80] for all
    ref_roi = warped_rgb[40:80, 30:70]
    ind1_roi = warped_rgb[40:80, 180:220]
    ind2_roi = warped_rgb[40:80, 310:350]
    
    # Calculate mean color channels
    ref_rgb = np.mean(ref_roi, axis=(0, 1))
    ind1_rgb = np.mean(ind1_roi, axis=(0, 1))
    ind2_rgb = np.mean(ind2_roi, axis=(0, 1))
    
    # Lighting Normalization Factors based on calibrator reference patch
    # Target Reference color is [224, 224, 224]
    factors = np.zeros(3, dtype=np.float32)
    for i in range(3):
        factors[i] = REF_TARGET[i] / max(1.0, ref_rgb[i])
        
    # Apply calibration
    ind1_calib = np.minimum(255.0, ind1_rgb * factors)
    ind2_calib = np.minimum(255.0, ind2_rgb * factors)

    # 1. Calculate Fungal Index (FI)
    # Delta relative to healthy base color
    delta_r1 = abs(ind1_calib[0] - IND1_HEALTHY[0])
    delta_g1 = abs(ind1_calib[1] - IND1_HEALTHY[1])
    delta_b1 = abs(ind1_calib[2] - IND1_HEALTHY[2])
    avg_delta1 = (delta_r1 + delta_g1 + delta_b1) / 3.0
    
    # Max possible delta is from Healthy to Strong Positive
    max_delta1 = np.mean(np.abs(IND1_STRONG - IND1_HEALTHY)) # (184+82+17)/3 = 94.33
    fi_score = min(100.0, (avg_delta1 / max_delta1) * 100.0)
    
    # 2. Calculate VOC Index (VI)
    delta_r2 = abs(ind2_calib[0] - IND2_HEALTHY[0])
    delta_g2 = abs(ind2_calib[1] - IND2_HEALTHY[1])
    delta_b2 = abs(ind2_calib[2] - IND2_HEALTHY[2])
    avg_delta2 = (delta_r2 + delta_g2 + delta_b2) / 3.0
    
    max_delta2 = np.mean(np.abs(IND2_STRONG - IND2_HEALTHY)) # (149+64+64)/3 = 92.33
    vi_score = min(100.0, (avg_delta2 / max_delta2) * 100.0)

    # 3. Calculate Combined Contamination Index (CCI)
    # Default weights: 60% Fungal Index, 40% VOC Index
    w_fi, w_vi = 0.6, 0.4
    cci_score = (w_fi * fi_score) + (w_vi * vi_score)

    # Calculate Euclidean Color Distance for storage/calibration calibration
    dist_ind1 = math.sqrt(delta_r1**2 + delta_g1**2 + delta_b1**2)
    dist_ind2 = math.sqrt(delta_r2**2 + delta_g2**2 + delta_b2**2)
    mean_euclidean = (dist_ind1 + dist_ind2) / 2.0

    risk_level, confidence = get_risk_level(cci_score)
    
    # Determine local trend (mock trend direction for visualization)
    if cci_score > 60:
        trend = "Rising"
    elif cci_score > 25:
        trend = "Stable"
    else:
        trend = "Declining"

    return {
        "fi_score": round(fi_score, 1),
        "vi_score": round(vi_score, 1),
        "cci_score": round(cci_score, 1),
        "euclidean_distance": round(mean_euclidean, 2),
        "risk_level": risk_level,
        "confidence": confidence,
        "trend": trend,
        "ref_rgb": [int(x) for x in ref_rgb],
        "ind1_rgb": [int(x) for x in ind1_calib],
        "ind2_rgb": [int(x) for x in ind2_calib],
        "detection_method": detection_method
    }
