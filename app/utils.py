import cv2
import numpy as np
import os

def ensure_directories():
    os.makedirs("static/images", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)

def generate_pwa_icon(size: int, path: str):
    """
    Generates a premium PWA icon with a modern logo mark.
    """
    # Create canvas: dark purple to black radial gradient
    img = np.zeros((size, size, 3), dtype=np.uint8)
    
    # Fill gradient
    for y in range(size):
        for x in range(size):
            # Distance from center
            dist = np.sqrt((x - size/2)**2 + (y - size/2)**2)
            factor = min(1.0, dist / (size * 0.7))
            # HSL: Dark Slate/Indigo to darker
            r = int(74 * (1.0 - factor * 0.5))
            g = int(20 * (1.0 - factor * 0.7))
            b = int(140 * (1.0 - factor * 0.4))
            img[y, x] = [b, g, r] # BGR
            
    # Draw Logo Symbol (S-like SporoSentinel node mark)
    center = size // 2
    r_outer = int(size * 0.35)
    r_inner = int(size * 0.20)
    
    # Draw circles and connections
    cv2.circle(img, (center, center), r_outer, (135, 206, 92), int(size * 0.05)) # Light green circle
    cv2.circle(img, (center, center), r_inner, (255, 77, 109), -1) # Coral center
    
    # Add modern typography letter 'S' in white
    font_scale = size / 200.0
    thickness = int(size * 0.08)
    cv2.putText(
        img, "S", 
        (center - int(size * 0.15), center + int(size * 0.18)), 
        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA
    )
    
    cv2.imwrite(path, img)

def generate_sample_strip(path: str, cci_level: str = "caution"):
    """
    Generates a realistic testing strip.
    Aspect Ratio 400x120.
    Reference Calibrator Patch: left.
    Indicator 1: middle.
    Indicator 2: right.
    """
    # Canvas
    img = np.ones((120, 400, 3), dtype=np.uint8) * 245 # Off-white plastic strip
    
    # Draw reference calibrator patch (Light Gray: BGR = 224, 224, 224)
    cv2.rectangle(img, (30, 40), (70, 80), (224, 224, 224), -1)
    # Add border
    cv2.rectangle(img, (30, 40), (70, 80), (200, 200, 200), 1)
    
    # Configure Indicator Colors based on desired CCI Level
    # Indicator 1: Healthy #2E8B57 (RGB), Mild #7A9E3A, Warning #B56576, Strong Positive #E63946
    # Indicator 2: Healthy #6A0DAD, Mild #8E44AD, Warning #C44569, Strong Positive #FF4D6D
    if cci_level == "safe":
        ind1 = [87, 139, 46]   # BGR for #2E8B57
        ind2 = [173, 13, 106]  # BGR for #6A0DAD
    elif cci_level == "monitor":
        ind1 = [58, 158, 122]  # BGR for #7A9E3A
        ind2 = [173, 68, 142]  # BGR for #8E44AD
    elif cci_level == "caution":
        ind1 = [118, 101, 181] # BGR for #B56576
        ind2 = [105, 69, 196]  # BGR for #C44569
    elif cci_level == "high_risk":
        # Mixed: Ind 1 warning, Ind 2 strong
        ind1 = [118, 101, 181] # BGR for #B56576
        ind2 = [109, 77, 255]  # BGR for #FF4D6D
    else: # critical
        ind1 = [70, 57, 230]   # BGR for #E63946
        ind2 = [109, 77, 255]  # BGR for #FF4D6D
        
    # Draw Indicator 1 Patch (Middle)
    cv2.rectangle(img, (180, 40), (220, 80), ind1, -1)
    cv2.rectangle(img, (180, 40), (220, 80), (200, 200, 200), 1)
    
    # Draw Indicator 2 Patch (Right)
    cv2.rectangle(img, (310, 40), (350, 80), ind2, -1)
    cv2.rectangle(img, (310, 40), (350, 80), (200, 200, 200), 1)
    
    # Add subtle indicator text markings (REF, IND1, IND2)
    cv2.putText(img, "REF", (35, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    cv2.putText(img, "IND 1", (182, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    cv2.putText(img, "IND 2", (312, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
    
    # Save image
    cv2.imwrite(path, img)

def generate_mock_pmtiles():
    """
    Creates a dummy pmtiles file structure to prevent fetch 404 errors.
    """
    mock_path = "static/regional_map.pmtiles"
    if not os.path.exists(mock_path):
        # A simple valid header or empty binary representation for PMTiles format
        with open(mock_path, "wb") as f:
            f.write(b"PMTiles\x03\x00\x00\x00") # Simple header

def generate_all_assets():
    ensure_directories()
    
    # Generate PWA Icons
    if not os.path.exists("static/images/icon-192.png"):
        generate_pwa_icon(192, "static/images/icon-192.png")
    if not os.path.exists("static/images/icon-512.png"):
        generate_pwa_icon(512, "static/images/icon-512.png")
        
    # Generate multiple sample strips for testing
    generate_sample_strip("static/images/sample_strip_safe.png", "safe")
    generate_sample_strip("static/images/sample_strip_monitor.png", "monitor")
    generate_sample_strip("static/images/sample_strip_caution.png", "caution")
    generate_sample_strip("static/images/sample_strip_critical.png", "critical")
    # Default sample strip path
    generate_sample_strip("static/images/sample_strip.png", "caution")
    
    # Generate Mock PMTiles file
    generate_mock_pmtiles()

if __name__ == "__main__":
    generate_all_assets()
    print("All mock and branding assets generated successfully.")
