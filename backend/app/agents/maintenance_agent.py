from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.services.openai_service import OpenAIService
from app.services.maps_service import GoogleMapsService
from app.services.notfication_service import NotificationSerivce
from app.models.user import Car, MaintenanceRecord
import asyncio

class MaintenanceAgent:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        self.maps_service = GoogleMapsService()
        self.notification_service = NotificationSerivce()
        
        # Maintenance intervals (miles)
        self.maintenance_intervals = {
            "oil_change": 5000,
            "tire_rotation": 7500,
            "brake_inspection": 12000,
            "air_filter": 15000,
            "transmission_service": 30000
        }
        
        # Time-based intervals (months)
        self.time_intervals = {
            "oil_change": 6,
            "brake_inspection": 12,
            "air_filter": 12
        }

    async def analyze_maintenance_needs(self, car: Car, maintenance_history: List[MaintenanceRecord]) -> Dict:
        """Analyze car's maintenance needs and return recommendations"""
        current_date = datetime.utcnow()
        recommendations = []
        
        for service_type, mile_interval in self.maintenance_intervals.items():
            last_service = self._get_last_service(maintenance_history, service_type)
            
            needs_service = False
            reason = ""
            
            if last_service:
                miles_since_service = car.current_mileage - last_service.mileage_at_service
                months_since_service = (current_date - last_service.date_performed).days / 30
                
                if miles_since_service >= mile_interval:
                    needs_service = True
                    reason = f"{miles_since_service} miles since last {service_type}"
                elif service_type in self.time_intervals and months_since_service >= self.time_intervals[service_type]:
                    needs_service = True
                    reason = f"{int(months_since_service)} months since last {service_type}"
            else:
                # No record of this service
                needs_service = True
                reason = f"No record of {service_type}"
            
            if needs_service:
                recommendations.append({
                    "service_type": service_type,
                    "reason": reason,
                    "priority": self._calculate_priority(service_type, car, last_service),
                    "estimated_cost": self._estimate_cost(service_type, car)
                })
        
        return {
            "car_id": car.id,
            "analysis_date": current_date,
            "recommendations": sorted(recommendations, key=lambda x: x["priority"], reverse=True)
        }

    async def proactive_maintenance_check(self, user_id: int) -> List[Dict]:
        """Main agent function - proactively check all user's cars"""
        # This would be called by Celery beat scheduler
        from app.database import get_db
        
        # Get user's cars and maintenance history
        # Analyze each car
        # Generate notifications for needed services
        # Research nearby shops
        # Send personalized recommendations
        
        pass  # Implementation continues...

    def _get_last_service(self, maintenance_history: List[MaintenanceRecord], service_type: str) -> Optional[MaintenanceRecord]:
        """Get the most recent service of a specific type"""
        services = [record for record in maintenance_history if record.service_type == service_type]
        return max(services, key=lambda x: x.date_performed) if services else None

    def _calculate_priority(self, service_type: str, car: Car, last_service: Optional[MaintenanceRecord]) -> int:
        """Calculate priority (1-10) for a maintenance item"""
        priority_map = {
            "oil_change": 10,  # Critical
            "brake_inspection": 9,
            "tire_rotation": 5,
            "air_filter": 4,
            "transmission_service": 7
        }
        return priority_map.get(service_type, 5)

    def _estimate_cost(self, service_type: str, car: Car) -> Dict:
        """Estimate cost range for a service"""
        # This could integrate with parts/labor cost APIs
        cost_estimates = {
            "oil_change": {"min": 30, "max": 80},
            "brake_inspection": {"min": 100, "max": 300},
            "tire_rotation": {"min": 20, "max": 50},
            "air_filter": {"min": 15, "max": 40},
            "transmission_service": {"min": 150, "max": 400}
        }
        return cost_estimates.get(service_type, {"min": 50, "max": 200})