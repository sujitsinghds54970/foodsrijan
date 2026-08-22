"""
AI Service for VaidyaVihar Diagnostic ERP

Provides AI-powered features:
- MenuItem recommendations based on symptoms
- Predictive analytics
- Anomaly detection
- Customer risk assessment
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import random


class SeverityLevel(str, Enum):
    """Symptom severity levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Symptom:
    """Symptom data structure"""
    name: str
    severity: str
    duration_days: int
    body_part: str
    description: Optional[str] = None


@dataclass
class MenuItemRecommendation:
    """MenuItem recommendation result"""
    test_code: str
    test_name: str
    category: str
    priority: str
    reason: str
    estimated_cost: float
    preparation_instructions: Optional[str] = None


@dataclass
class RiskAssessment:
    """Customer risk assessment"""
    risk_score: int  # 0-100
    risk_level: str
    risk_factors: List[str]
    recommendations: List[str]
    follow_up_required: bool
    urgency: str


class SymptomAnalyzer:
    """Analyzes symptoms and suggests appropriate menu_items"""

    # Symptom to test mapping
    SYMPTOM_TEST_MAP = {
        # General / Routine
        "fever": [
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Detect infection", 300),
            ("CRP", "C-Reactive Protein", "pathology", "moderate", "Check inflammation", 400),
            ("WIDAL", "Widal MenuItem", "pathology", "moderate", "Rule out typhoid", 350),
        ],
        "fatigue": [
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Check for anemia", 300),
            ("LFT", "Liver Function MenuItem", "pathology", "moderate", "Check liver health", 600),
            ("KFT", "Kidney Function MenuItem", "pathology", "moderate", "Check kidney health", 500),
            ("TSH", "Thyroid Stimulating Hormone", "pathology", "moderate", "Check thyroid", 450),
            ("Vitamin B12", "Vitamin B12 Level", "pathology", "low", "Check B12 deficiency", 800),
            ("Vitamin D", "Vitamin D Level", "pathology", "low", "Check vitamin D", 1200),
        ],
        "weight_loss": [
            ("CBC", "Complete Blood Count", "pathology", "high", "Check for infections/cancer", 300),
            ("LFT", "Liver Function MenuItem", "pathology", "high", "Check liver function", 600),
            ("KFT", "Kidney Function MenuItem", "pathology", "high", "Check kidney function", 500),
            ("FBS", "Fasting Blood Sugar", "pathology", "high", "Check diabetes", 100),
            ("HbA1c", "HbA1c MenuItem", "pathology", "moderate", "Check long-term sugar", 400),
            ("Thyroid Panel", "Thyroid Profile", "pathology", "moderate", "Check thyroid", 700),
        ],
        "chest_pain": [
            ("ECG", "Electrocardiogram", "cardiology", "critical", "Check heart rhythm", 300),
            ("2D Echo", "2D Echocardiography", "cardiology", "critical", "Check heart structure", 2500),
            ("Troponin I", "Troponin I", "pathology", "critical", "Detect heart attack", 800),
            ("CXR", "Chest X-Ray", "radiology", "high", "Check lungs/heart", 400),
            ("Lipid Profile", "Lipid Profile", "pathology", "moderate", "Check cholesterol", 600),
        ],
        "shortness_of_breath": [
            ("ECG", "Electrocardiogram", "cardiology", "high", "Check heart function", 300),
            ("2D Echo", "2D Echocardiography", "cardiology", "high", "Check heart structure", 2500),
            ("CXR", "Chest X-Ray", "radiology", "high", "Check lungs", 400),
            ("PFT", "Pulmonary Function MenuItem", "pulmonology", "moderate", "Check lung function", 1200),
            ("D-Dimer", "D-Dimer MenuItem", "pathology", "high", "Rule out clot", 600),
        ],
        "headache": [
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Check for infection", 300),
            ("MRI Brain", "MRI Brain", "radiology", "moderate", "Check brain structure", 4500),
            ("CT Brain", "CT Scan Brain", "radiology", "moderate", "Check for tumors/bleed", 2500),
            ("ESR", "Erythrocyte Sedimentation Rate", "pathology", "low", "Check inflammation", 150),
            ("Eye MenuItem", "Eye Examination", "opthalmology", "low", "Check vision", 200),
        ],
        "abdominal_pain": [
            ("USG Whole Abdomen", "Ultrasound Whole Abdomen", "radiology", "high", "Check abdominal organs", 800),
            ("LFT", "Liver Function MenuItem", "pathology", "high", "Check liver", 600),
            ("KFT", "Kidney Function MenuItem", "pathology", "high", "Check kidneys", 500),
            ("Amylase", "Serum Amylase", "pathology", "moderate", "Check pancreas", 300),
            ("Lipase", "Serum Lipase", "pathology", "moderate", "Check pancreas", 350),
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Check infection", 300),
        ],
        "joint_pain": [
            ("RA Factor", "Rheumatoid Factor", "pathology", "moderate", "Check arthritis", 400),
            ("CRP", "C-Reactive Protein", "pathology", "moderate", "Check inflammation", 400),
            ("ESR", "Erythrocyte Sedimentation Rate", "pathology", "moderate", "Check inflammation", 150),
            ("Uric Acid", "Serum Uric Acid", "pathology", "moderate", "Check gout", 250),
            ("Anti-CCP", "Anti-CCP Antibody", "pathology", "moderate", "Check rheumatoid arthritis", 1200),
            ("Vitamin D", "Vitamin D Level", "pathology", "low", "Check deficiency", 1200),
        ],
        "skin_rash": [
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Check infection", 300),
            ("Allergy Panel", "Allergy MenuItem Panel", "pathology", "moderate", "Identify allergens", 2500),
            ("Thyroid Panel", "Thyroid Profile", "pathology", "low", "Check thyroid", 700),
            ("Skin Scraping", "Skin Scraping Examination", "pathology", "low", "Check fungal infection", 200),
        ],
        "urinary_symptoms": [
            ("Urine Routine", "Urine Routine Examination", "pathology", "high", "Check infection", 150),
            ("Urine Culture", "Urine Culture & Sensitivity", "pathology", "high", "Identify bacteria", 400),
            ("KFT", "Kidney Function MenuItem", "pathology", "moderate", "Check kidney function", 500),
            ("Ultrasound KUB", "Ultrasound KUB", "radiology", "moderate", "Check kidneys/bladder", 800),
        ],
        "digestive_issues": [
            ("LFT", "Liver Function MenuItem", "pathology", "moderate", "Check liver", 600),
            ("Lipid Profile", "Lipid Profile", "pathology", "low", "Check cholesterol", 600),
            ("FBS", "Fasting Blood Sugar", "pathology", "moderate", "Check diabetes", 100),
            ("Thyroid Panel", "Thyroid Profile", "pathology", "moderate", "Check thyroid", 700),
            ("USG Whole Abdomen", "Ultrasound Whole Abdomen", "radiology", "moderate", "Check organs", 800),
        ],
        "dizziness": [
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Check anemia", 300),
            ("ECG", "Electrocardiogram", "cardiology", "moderate", "Check heart", 300),
            ("Blood Pressure", "BP Monitoring", "general", "moderate", "Check BP", 50),
            ("Vitamin B12", "Vitamin B12 Level", "pathology", "low", "Check deficiency", 800),
            ("TSH", "Thyroid Stimulating Hormone", "pathology", "low", "Check thyroid", 450),
        ],
        "cough": [
            ("CXR", "Chest X-Ray", "radiology", "high", "Check lungs", 400),
            ("CBC", "Complete Blood Count", "pathology", "moderate", "Check infection", 300),
            ("Sputum Culture", "Sputum Culture", "pathology", "moderate", "Identify bacteria", 500),
            ("TB Panel", "TB Detection Panel", "pathology", "moderate", "Rule out TB", 800),
        ],
        "leg_swelling": [
            ("2D Echo", "2D Echocardiography", "cardiology", "high", "Check heart function", 2500),
            ("KFT", "Kidney Function MenuItem", "pathology", "high", "Check kidney function", 500),
            ("LFT", "Liver Function MenuItem", "pathology", "moderate", "Check liver", 600),
            ("D-Dimer", "D-Dimer MenuItem", "pathology", "high", "Rule out clot", 600),
            ("Venous Doppler", "Venous Doppler Lower Limb", "radiology", "moderate", "Check veins", 2000),
        ],
        "eye_problems": [
            ("Eye MenuItem", "Comprehensive Eye Examination", "opthalmology", "moderate", "Check vision", 300),
            ("Refraction", "Refraction MenuItem", "opthalmology", "low", "Check prescription", 150),
            ("Fundus", "Fundus Examination", "opthalmology", "moderate", "Check retina", 200),
            ("Tonometry", "Tonometry (Eye Pressure)", "opthalmology", "moderate", "Check glaucoma", 100),
        ],
        "ear_problems": [
            ("ENT Examination", "ENT Consultation", "ent", "moderate", "Examine ears", 300),
            ("Audiometry", "Audiometry MenuItem", "ent", "moderate", "Check hearing", 400),
            ("Tympanometry", "Tympanometry", "ent", "moderate", "Check eardrum", 300),
        ],
    }

    # Gender-specific test recommendations
    GENDER_TESTS = {
        "female": [
            ("Pap Smear", "Pap Smear MenuItem", "gynecology", "moderate", "Cervical cancer screening", 500),
            ("Mammography", "Mammography", "radiology", "moderate", "Breast cancer screening", 1200),
            ("CA125", "CA-125 Tumor Marker", "pathology", "moderate", "Ovarian cancer marker", 800),
            ("AMH", "Anti-Mullerian Hormone", "pathology", "moderate", "Fertility assessment", 1500),
        ],
        "male": [
            ("PSA", "Prostate Specific Antigen", "pathology", "moderate", "Prostate cancer screening", 400),
            ("MenuItemosterone", "Serum MenuItemosterone", "pathology", "low", "Hormone level check", 600),
        ]
    }

    # Age-specific routine menu_items
    AGE_TESTS = {
        (0, 18): [  # Children
            ("CBC", "Complete Blood Count", "pathology", "low", "General health check", 300),
            ("Vitamin D", "Vitamin D Level", "pathology", "low", "Check deficiency", 1200),
        ],
        (18, 40): [  # Young adults
            ("CBC", "Complete Blood Count", "pathology", "low", "General health", 300),
            ("Lipid Profile", "Lipid Profile", "pathology", "low", "Cholesterol check", 600),
            ("FBS", "Fasting Blood Sugar", "pathology", "low", "Diabetes check", 100),
        ],
        (40, 60): [  # Middle age
            ("CBC", "Complete Blood Count", "pathology", "low", "General health", 300),
            ("Lipid Profile", "Lipid Profile", "pathology", "moderate", "Cholesterol", 600),
            ("HbA1c", "HbA1c MenuItem", "pathology", "moderate", "Diabetes check", 400),
            ("KFT", "Kidney Function MenuItem", "pathology", "low", "Kidney health", 500),
            ("LFT", "Liver Function MenuItem", "pathology", "low", "Liver health", 600),
            ("ECG", "Electrocardiogram", "cardiology", "low", "Heart check", 300),
        ],
        (60, 100): [  # Senior citizens
            ("CBC", "Complete Blood Count", "pathology", "moderate", "General health", 300),
            ("Lipid Profile", "Lipid Profile", "pathology", "moderate", "Cholesterol", 600),
            ("HbA1c", "HbA1c MenuItem", "pathology", "moderate", "Diabetes check", 400),
            ("KFT", "Kidney Function MenuItem", "pathology", "moderate", "Kidney health", 500),
            ("LFT", "Liver Function MenuItem", "pathology", "moderate", "Liver health", 600),
            ("ECG", "Electrocardiogram", "cardiology", "moderate", "Heart check", 300),
            ("2D Echo", "2D Echocardiography", "cardiology", "moderate", "Heart structure", 2500),
            ("TSH", "Thyroid Stimulating Hormone", "pathology", "low", "Thyroid check", 450),
            ("Vitamin B12", "Vitamin B12 Level", "pathology", "low", "Check deficiency", 800),
            ("Vitamin D", "Vitamin D Level", "pathology", "low", "Check deficiency", 1200),
        ]
    }

    @classmethod
    def analyze_symptoms(
        cls,
        symptoms: List[Dict],
        age: int,
        gender: str,
        medical_history: Optional[List[str]] = None
    ) -> List[MenuItemRecommendation]:
        """
        Analyze symptoms and return test recommendations
        
        Args:
            symptoms: List of symptom dictionaries
            age: Customer age
            gender: Customer gender
            medical_history: List of existing conditions
            
        Returns:
            List of test recommendations
        """
        recommendations = []
        seen_menu_items = set()
        severity_map = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
        
        # Process each symptom
        for symptom in symptoms:
            symptom_name = symptom.get("name", "").lower()
            severity = symptom.get("severity", "moderate")
            duration = symptom.get("duration_days", 1)
            
            # Boost priority for long duration
            if duration > 7:
                severity = "high"
            elif duration > 14:
                severity = "critical"
            
            # Find matching menu_items
            for key, menu_items in cls.SYMPTOM_TEST_MAP.items():
                if key in symptom_name:
                    for test in menu_items:
                        test_code, test_name, category, priority, reason, cost = test
                        
                        # Adjust priority based on severity
                        if severity_map.get(severity, 2) > severity_map.get(priority, 2):
                            priority = severity
                        
                        # Add to recommendations if not already added
                        if test_code not in seen_menu_items:
                            seen_menu_items.add(test_code)
                            recommendations.append(MenuItemRecommendation(
                                test_code=test_code,
                                test_name=test_name,
                                category=category,
                                priority=priority,
                                reason=reason,
                                estimated_cost=cost,
                                preparation_instructions=cls._get_preparation_instructions(test_code)
                            ))
        
        # Add gender-specific menu_items
        if gender.lower() in cls.GENDER_TESTS:
            for test in cls.GENDER_TESTS[gender.lower()]:
                test_code, test_name, category, priority, reason, cost = test
                if test_code not in seen_menu_items:
                    seen_menu_items.add(test_code)
                    recommendations.append(MenuItemRecommendation(
                        test_code=test_code,
                        test_name=test_name,
                        category=category,
                        priority=priority,
                        reason=reason,
                        estimated_cost=cost,
                        preparation_instructions=cls._get_preparation_instructions(test_code)
                    ))
        
        # Add age-appropriate routine menu_items
        for age_range, menu_items in cls.AGE_TESTS.items():
            if age_range[0] <= age <= age_range[1]:
                for test in menu_items:
                    test_code, test_name, category, priority, reason, cost = test
                    if test_code not in seen_menu_items:
                        seen_menu_items.add(test_code)
                        recommendations.append(MenuItemRecommendation(
                            test_code=test_code,
                            test_name=test_name,
                            category=category,
                            priority=priority,
                            reason=reason,
                            estimated_cost=cost,
                            preparation_instructions=cls._get_preparation_instructions(test_code)
                        ))
                break
        
        # Sort by priority (critical first)
        priority_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        recommendations.sort(key=lambda x: priority_order.get(x.priority, 3))
        
        return recommendations

    @staticmethod
    def _get_preparation_instructions(test_code: str) -> Optional[str]:
        """Get preparation instructions for a test"""
        instructions = {
            "FBS": "Fast for 8-10 hours before the test. Only water is allowed.",
            "Lipid Profile": "Fast for 9-12 hours before the test.",
            "LFT": "Fast for 8-10 hours for accurate results.",
            "KFT": "No special preparation required.",
            "CBC": "No special preparation required.",
            "TSH": "No fasting required. Take thyroid medications after the test.",
            "HbA1c": "No fasting required. Can be done at any time of day.",
            "Vitamin D": "No fasting required.",
            "Vitamin B12": "No fasting required.",
            "2D Echo": "No special preparation required.",
            "ECG": "No fasting required. Avoid caffeine before the test.",
            "CXR": "No special preparation required. Remove metal jewelry.",
            "USG Whole Abdomen": "Fast for 6-8 hours before the test. Drink water and hold urine.",
            "CT Brain": "No special preparation. Remove metal objects.",
            "MRI Brain": "No metal objects. Inform about implants.",
            "Thyroid Panel": "No fasting required.",
        }
        return instructions.get(test_code)

    @classmethod
    def get_common_symptoms(cls) -> List[Dict]:
        """Get list of common symptoms for UI dropdowns"""
        return [
            {"id": "fever", "name": "Fever", "body_parts": ["General"], "severities": ["low", "moderate", "high"]},
            {"id": "fatigue", "name": "Fatigue", "body_parts": ["General"], "severities": ["low", "moderate", "high"]},
            {"id": "chest_pain", "name": "Chest Pain", "body_parts": ["Chest"], "severities": ["moderate", "high", "critical"]},
            {"id": "headache", "name": "Headache", "body_parts": ["Head"], "severities": ["low", "moderate", "high", "critical"]},
            {"id": "abdominal_pain", "name": "Abdominal Pain", "body_parts": ["Abdomen"], "severities": ["moderate", "high", "critical"]},
            {"id": "shortness_of_breath", "name": "Shortness of Breath", "body_parts": ["Chest", "Lungs"], "severities": ["moderate", "high", "critical"]},
            {"id": "joint_pain", "name": "Joint Pain", "body_parts": ["Joints", "Bones"], "severities": ["low", "moderate", "high"]},
            {"id": "urinary_symptoms", "name": "Urinary Symptoms", "body_parts": ["Urinary"], "severities": ["moderate", "high"]},
            {"id": "skin_rash", "name": "Skin Rash", "body_parts": ["Skin"], "severities": ["low", "moderate"]},
            {"id": "cough", "name": "Cough", "body_parts": ["Throat", "Lungs"], "severities": ["low", "moderate", "high"]},
            {"id": "leg_swelling", "name": "Leg Swelling", "body_parts": ["Legs"], "severities": ["moderate", "high"]},
            {"id": "dizziness", "name": "Dizziness", "body_parts": ["Head"], "severities": ["low", "moderate", "high"]},
            {"id": "weight_loss", "name": "Unexplained Weight Loss", "body_parts": ["General"], "severities": ["high", "critical"]},
            {"id": "eye_problems", "name": "Eye Problems", "body_parts": ["Eyes"], "severities": ["low", "moderate", "high"]},
            {"id": "ear_problems", "name": "Ear Problems", "body_parts": ["Ears"], "severities": ["low", "moderate"]},
            {"id": "digestive_issues", "name": "Digestive Issues", "body_parts": ["Abdomen", "Stomach"], "severities": ["low", "moderate", "high"]},
        ]


class PredictiveAnalytics:
    """Provides predictive analytics for the diagnostic center"""

    @staticmethod
    def predict_no_show_probability(
        patient_id: str,
        appointment_history: List[Dict],
        day_of_week: int,
        time_slot: str
    ) -> float:
        """
        Predict probability of patient no-show
        
        Returns:
            Probability (0-1) of no-show
        """
        base_probability = 0.15  # Base 15% no-show rate
        
        # Adjust based on history
        no_show_count = sum(1 for appt in appointment_history if appt.get("status") == "no_show")
        total_appointments = len(appointment_history)
        
        if total_appointments > 0:
            no_show_rate = no_show_count / total_appointments
            base_probability = max(0.05, min(0.5, base_probability + (no_show_rate - 0.15)))
        
        # Day of week adjustment (weekends have higher no-show)
        if day_of_week in [5, 6]:  # Saturday, Sunday
            base_probability += 0.05
        
        # Time slot adjustment (early morning and late evening have higher no-show)
        if time_slot in ["07:00", "08:00", "19:00", "20:00"]:
            base_probability += 0.03
        
        return round(base_probability, 2)

    @staticmethod
    def predict_revenue(
        branch_id: str,
        historical_data: List[Dict],
        days_ahead: int = 30
    ) -> Dict:
        """
        Predict revenue for upcoming period
        
        Returns:
            Dictionary with predicted revenue
        """
        if not historical_data:
            return {
                "predicted_revenue": 0,
                "confidence": 0,
                "breakdown": {}
            }
        
        # Calculate average daily revenue
        daily_revenues = [day.get("revenue", 0) for day in historical_data]
        avg_daily = sum(daily_revenues) / len(daily_revenues)
        
        # Simple prediction
        predicted_daily = avg_daily * (1 + random.uniform(-0.1, 0.1))  # Add some variance
        
        total_predicted = predicted_daily * days_ahead
        
        return {
            "predicted_revenue": round(total_predicted, 2),
            "confidence": round(0.7 + random.uniform(-0.1, 0.1), 2),  # Mock confidence
            "daily_average": round(predicted_daily, 2),
            "period_days": days_ahead
        }

    @staticmethod
    def detect_anomaly(
        value: float,
        historical_values: List[float],
        threshold: float = 2.0
    ) -> Tuple[bool, float]:
        """
        Detect if a value is anomalous based on historical data
        
        Returns:
            (is_anomaly, z_score)
        """
        if not historical_values:
            return False, 0.0
        
        import statistics
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 1
        
        if stdev == 0:
            return False, 0.0
        
        z_score = abs((value - mean) / stdev)
        return z_score > threshold, round(z_score, 2)


class RiskAssessmentEngine:
    """Assesses patient health risks"""

    @classmethod
    def assess_patient_risk(
        cls,
        age: int,
        gender: str,
        medical_history: List[str],
        lab_results: Dict[str, float],
        lifestyle_factors: Dict[str, str]
    ) -> RiskAssessment:
        """
        Assess patient health risk
        
        Returns:
            Risk assessment with score and recommendations
        """
        risk_score = 0
        risk_factors = []
        recommendations = []
        follow_up_required = False
        urgency = "routine"
        
        # Age-based risk
        if age < 30:
            risk_score += 5
        elif age < 50:
            risk_score += 15
        elif age < 70:
            risk_score += 25
        else:
            risk_score += 40
            follow_up_required = True
        
        # Medical history risk
        risk_conditions = ["diabetes", "hypertension", "heart_disease", "cancer", "asthma", "arthritis"]
        for condition in medical_history:
            if condition.lower() in risk_conditions:
                risk_score += 15
                risk_factors.append(f"History of {condition}")
        
        # Lab result risk assessment
        critical_ranges = {
            "blood_glucose": {"high": 200, "low": 70},
            "blood_pressure_systolic": {"high": 180, "low": 90},
            "cholesterol": {"high": 240, "low": 0},
            "hemoglobin": {"high": 18, "low": 12},
        }
        
        for test, value in lab_results.items():
            if test in critical_ranges:
                ranges = critical_ranges[test]
                if value > ranges["high"]:
                    risk_score += 20
                    risk_factors.append(f"Elevated {test}")
                    follow_up_required = True
                    urgency = "soon" if urgency == "routine" else urgency
                elif value < ranges["low"]:
                    risk_score += 15
                    risk_factors.append(f"Low {test}")
        
        # Lifestyle risk factors
        if lifestyle_factors.get("smoking") == "yes":
            risk_score += 20
            risk_factors.append("Smoking habit")
        
        if lifestyle_factors.get("alcohol") == "frequent":
            risk_score += 15
            risk_factors.append("Frequent alcohol consumption")
        
        if lifestyle_factors.get("exercise") == "none":
            risk_score += 10
            risk_factors.append("Sedentary lifestyle")
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "high"
            urgency = "urgent"
            follow_up_required = True
            recommendations = [
                "Immediate consultation with physician recommended",
                "Schedule follow-up within 1 week",
                "Regular monitoring of vital signs",
                "Consider specialist referral"
            ]
        elif risk_score >= 50:
            risk_level = "moderate"
            urgency = "soon"
            recommendations = [
                "Consultation with physician recommended",
                "Schedule follow-up within 2 weeks",
                "Monitor symptoms regularly",
                "Consider lifestyle modifications"
            ]
        elif risk_score >= 25:
            risk_level = "low"
            recommendations = [
                "Regular health check-ups",
                "Maintain healthy lifestyle",
                "Monitor any symptoms"
            ]
        else:
            risk_level = "minimal"
            recommendations = [
                "Continue routine health monitoring",
                "Annual health check-up recommended"
            ]
        
        return RiskAssessment(
            risk_score=min(risk_score, 100),
            risk_level=risk_level,
            risk_factors=risk_factors if risk_factors else ["No significant risk factors identified"],
            recommendations=recommendations,
            follow_up_required=follow_up_required,
            urgency=urgency
        )


# Convenience functions
def get_test_recommendations(
    symptoms: List[Dict],
    age: int,
    gender: str,
    medical_history: List[str] = None
) -> List[MenuItemRecommendation]:
    """Get test recommendations based on symptoms"""
    return SymptomAnalyzer.analyze_symptoms(symptoms, age, gender, medical_history)


def assess_patient_risk(
    age: int,
    gender: str,
    medical_history: List[str],
    lab_results: Dict[str, float],
    lifestyle: Dict[str, str]
) -> RiskAssessment:
    """Assess patient health risk"""
    return RiskAssessmentEngine.assess_patient_risk(
        age, gender, medical_history, lab_results, lifestyle
    )


def get_common_symptoms() -> List[Dict]:
    """Get common symptoms for UI"""
    return SymptomAnalyzer.get_common_symptoms()

