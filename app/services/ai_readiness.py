from abc import ABC, abstractmethod
import random
from typing import Dict, Any, List

class IFungalOutbreakPredictor(ABC):
    """
    Interface for predicting regional fungal outbreaks based on regional climate,
    soil data, and aggregated local scans.
    """
    @abstractmethod
    def predict_regional_outbreak(self, region: str) -> Dict[str, Any]:
        pass

class IContaminationForecaster(ABC):
    """
    Interface for forecasting a specific storage facility's CCI trend
    based on historical scan progression and storage conditions.
    """
    @abstractmethod
    def forecast_grain_cci(self, scan_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        pass

class IRecommendationOptimizer(ABC):
    """
    Interface for optimizing storage recommendations and remedial paths
    using cost-benefit models and localized agent reports.
    """
    @abstractmethod
    def optimize_remediation_path(self, cci_score: float, region: str) -> Dict[str, Any]:
        pass


# Baseline implementations for immediate use (AI-Readiness Mocks)

class MockFungalOutbreakPredictor(IFungalOutbreakPredictor):
    def predict_regional_outbreak(self, region: str) -> Dict[str, Any]:
        # Outbreak probability calculation simulation
        base_probs = {
            "High-humidity Coastal": 72.5,
            "Aspergillus-prone South": 84.0,
            "Northern Grain Belt": 15.0,
            "Western Drylands": 32.0,
            "Global": 45.0
        }
        
        prob = base_probs.get(region, 35.0)
        # Add slight variation simulating realtime sensory telemetry
        prob = min(99.0, max(1.0, prob + random.uniform(-5.0, 5.0)))
        
        status = "Safe"
        if prob > 75:
            status = "Critical Outbreak Warning"
        elif prob > 50:
            status = "Moderate Alert"
        elif prob > 25:
            status = "Low Alert"
            
        return {
            "region": region,
            "outbreak_probability": round(prob, 1),
            "threat_status": status,
            "primary_pathogen": "Aspergillus flavus" if "South" in region or "Coastal" in region else "Penicillium chrysogenum",
            "model_version": "SporoPredict-v1.0.2-alpha",
            "confidence_interval": [round(prob - 4.5, 1), round(min(100.0, prob + 4.5), 1)]
        }

class MockContaminationForecaster(IContaminationForecaster):
    def forecast_grain_cci(self, scan_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Forecast logic based on historical values
        if not scan_history:
            return {
                "forecast_trend": "Insufficient Data",
                "days_to_threshold_80": -1,
                "projected_cci_7_days": 0.0,
                "projected_cci_14_days": 0.0,
                "model_version": "GrainForecaster-v0.8.1-beta"
            }
            
        # Get last CCI scores
        ccis = [scan["cci_score"] for scan in scan_history]
        last_cci = ccis[-1]
        
        # Simple linear projection model simulation
        if len(ccis) >= 2:
            delta = ccis[-1] - ccis[0]
            slope = delta / len(ccis)
        else:
            slope = 1.2 # Default slow rise under standard humidity
            
        proj_7 = min(100.0, max(0.0, last_cci + (slope * 7)))
        proj_14 = min(100.0, max(0.0, last_cci + (slope * 14)))
        
        # Calculate days to reach critical threshold (CCI = 80)
        if slope > 0:
            days_to_80 = int((80.0 - last_cci) / slope)
            if days_to_80 < 0:
                days_to_80 = 0 # Already critical
        else:
            days_to_80 = -1 # Declining, won't reach threshold
            
        trend = "Stable"
        if slope > 1.5:
            trend = "Accelerating Contamination"
        elif slope > 0.5:
            trend = "Slow Growth"
        elif slope < -0.5:
            trend = "Fungal Decay Halting"
            
        return {
            "forecast_trend": trend,
            "days_to_threshold_80": days_to_80,
            "projected_cci_7_days": round(proj_7, 1),
            "projected_cci_14_days": round(proj_14, 1),
            "model_version": "GrainForecaster-v0.8.1-beta",
            "daily_growth_rate": round(slope, 2)
        }

class MockRecommendationOptimizer(IRecommendationOptimizer):
    def optimize_remediation_path(self, cci_score: float, region: str) -> Dict[str, Any]:
        # Mocking an optimal recommendation path selection
        actions = []
        if cci_score <= 20:
            actions = ["Maintain hermetic sealing", "Perform regular monthly checks"]
            cost = "Low"
            success_rate = 98.0
        elif cci_score <= 40:
            actions = ["Activate silo ventilation for 3 hours daily", "Re-sample grain batch in 48 hours"]
            cost = "Low"
            success_rate = 92.5
        elif cci_score <= 60:
            actions = ["Activate continuous dynamic aeration", "Reduce grain moisture to <13.5% immediately", "Apply organic acid preservatives"]
            cost = "Moderate"
            success_rate = 85.0
        elif cci_score <= 80:
            actions = ["Quarantine the storage unit", "Physically separate contaminated layers", "Deploy mobile heating drying units"]
            cost = "High"
            success_rate = 74.0
        else:
            actions = ["Complete bin evacuation", "Redirect batch to non-food/biofuel applications", "Sanitize storage structure with fungicidal agents"]
            cost = "Very High"
            success_rate = 99.0
            
        return {
            "optimized_actions": actions,
            "estimated_remediation_cost": cost,
            "predicted_success_rate": success_rate,
            "model_version": "RemediateOpt-v2.0-rc1"
        }
