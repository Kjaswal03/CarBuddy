# app/agents/autonomous_maintenance_agent.py
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
from app.services.openai_service import OpenAIService
from app.services.maps_service import GoogleMapsService
from app.services.notfication_service import NotificationService
from app.models.user import User, Car, MaintenanceRecord

class AutonomousMaintenanceAgent:
    """Autonomous agent that proactively manages car maintenance"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self.maps_service = GoogleMapsService()
        self.notification_service = NotificationService()
        
        # Agent's knowledge base
        self.maintenance_rules = {
            "oil_change": {
                "mileage_interval": 5000,
                "time_interval_months": 6,
                "priority": 10,
                "safety_critical": True
            },
            "brake_inspection": {
                "mileage_interval": 12000,
                "time_interval_months": 12,
                "priority": 9,
                "safety_critical": True
            },
            "tire_rotation": {
                "mileage_interval": 7500,
                "time_interval_months": 6,
                "priority": 6,
                "safety_critical": False
            }
        }
    
    async def autonomous_daily_check(self):
        """Main autonomous function - runs daily to check all users"""
        print(f"🤖 CarBuddy Agent starting daily check at {datetime.now()}")
        
        # Get all active users (this would come from database)
        active_users = await self._get_active_users()
        
        for user in active_users:
            try:
                await self._analyze_user_cars(user)
            except Exception as e:
                print(f"Error analyzing user {user.id}: {e}")
        
        print("🤖 Daily check complete")
    
    async def _analyze_user_cars(self, user: User):
        """Analyze all cars for a specific user"""
        for car in user.cars:
            context = await self._build_car_context(car)
            
            # Use AI to analyze the situation
            recommendations = await self.openai_service.generate_maintenance_recommendation(
                car_data=context["car_data"],
                maintenance_history=context["maintenance_history"]
            )
            
            # Decide what autonomous actions to take
            action_plan = await self.openai_service.decide_autonomous_action(context)
            
            # Execute autonomous actions
            await self._execute_autonomous_actions(user, car, action_plan)
    
    async def _build_car_context(self, car: Car) -> Dict:
        """Build comprehensive context about a car for AI analysis"""
        maintenance_history = await self._get_maintenance_history(car.id)
        
        # Calculate time/mileage since last services
        service_status = {}
        for service_type in self.maintenance_rules.keys():
            last_service = self._find_last_service(maintenance_history, service_type)
            service_status[service_type] = self._calculate_service_status(car, last_service, service_type)
        
        return {
            "car_data": {
                "id": car.id,
                "make": car.make,
                "model": car.model,
                "year": car.year,
                "current_mileage": car.current_mileage,
                "age_years": datetime.now().year - car.year
            },
            "maintenance_history": [
                {
                    "service_type": record.service_type,
                    "date": record.date_performed.isoformat(),
                    "mileage": record.mileage_at_service,
                    "cost": record.cost
                } for record in maintenance_history
            ],
            "service_status": service_status,
            "user_preferences": await self._get_user_preferences(car.user_id)
        }
    
    async def _execute_autonomous_actions(self, user: User, car: Car, action_plan: Dict):
        """Execute the actions decided by the AI agent"""
        for action in action_plan.get("actions", []):
            action_type = action.get("type")
            
            if action_type == "notification":
                await self._send_proactive_notification(user, car, action)
            
            elif action_type == "research_mechanics":
                await self._research_and_recommend_mechanics(user, car, action)
            
            elif action_type == "schedule_followup":
                await self._schedule_followup_check(user, car, action)
            
            elif action_type == "price_research":
                await self._research_service_prices(user, car, action)
    
    async def _send_proactive_notification(self, user: User, car: Car, action: Dict):
        """Send proactive maintenance notification"""
        message = action.get("message", "")
        priority = action.get("priority", "medium")
        
        # Personalize the message
        personalized_message = f"Hi! Your {car.year} {car.make} {car.model} {message}"
        
        notification_data = {
            "user_id": user.id,
            "car_id": car.id,
            "message": personalized_message,
            "type": "maintenance_reminder",
            "priority": priority,
            "action_required": True
        }
        
        # Send via multiple channels based on priority
        if priority == "high":
            await self.notification_service.send_push_notification(user.id, personalized_message)
            await self.notification_service.send_sms(user.phone, personalized_message)
        else:
            await self.notification_service.send_push_notification(user.id, personalized_message)
        
        # Log the autonomous action
        await self._log_agent_action("proactive_notification", user.id, car.id, notification_data)
    
    async def _research_and_recommend_mechanics(self, user: User, car: Car, action: Dict):
        """Autonomously research and recommend mechanics"""
        service_type = action.get("service_type", "general")
        
        # Get user's location (this would come from user profile or last known location)
        user_location = await self._get_user_location(user.id)
        
        # Research nearby mechanics
        mechanics = await self.maps_service.find_nearby_mechanics(
            location=user_location,
            service_type=service_type,
            radius_miles=25
        )
        
        # Filter and rank mechanics
        recommended_mechanics = await self._rank_mechanics(mechanics, service_type)
        
        # Send recommendation
        recommendation_message = self._format_mechanic_recommendations(recommended_mechanics[:3])
        
        await self.notification_service.send_push_notification(
            user.id, 
            f"I found some great options for your {service_type}:\n{recommendation_message}"
        )
    
    def _calculate_service_status(self, car: Car, last_service: Optional[MaintenanceRecord], service_type: str) -> Dict:
        """Calculate current status of a maintenance item"""
        rules = self.maintenance_rules.get(service_type, {})
        
        if not last_service:
            return {
                "status": "overdue",
                "reason": f"No record of {service_type}",
                "miles_overdue": car.current_mileage,
                "priority": rules.get("priority", 5)
            }
        
        miles_since = car.current_mileage - last_service.mileage_at_service
        days_since = (datetime.now() - last_service.date_performed).days
        months_since = days_since / 30
        
        mile_interval = rules.get("mileage_interval", 10000)
        time_interval = rules.get("time_interval_months", 12)
        
        overdue_miles = miles_since - mile_interval
        overdue_months = months_since - time_interval
        
        if overdue_miles > 0 or overdue_months > 0:
            status = "overdue"
        elif miles_since > (mile_interval * 0.8) or months_since > (time_interval * 0.8):
            status = "due_soon"
        else:
            status = "current"
        
        return {
            "status": status,
            "miles_since": miles_since,
            "months_since": months_since,
            "overdue_miles": max(0, overdue_miles),
            "overdue_months": max(0, overdue_months),
            "priority": rules.get("priority", 5)
        }

    async def _get_active_users(self) -> List[User]:
        """Get all active users from database"""
        # This would be implemented with your database layer
        # For now, returning empty list as example
        return []
    
    async def _get_maintenance_history(self, car_id: int) -> List[MaintenanceRecord]:
        """Get maintenance history for a car"""
        # Database query implementation
        return []
    
    def _find_last_service(self, maintenance_history: List[MaintenanceRecord], service_type: str) -> Optional[MaintenanceRecord]:
        """Find the most recent service of a specific type"""
        services = [record for record in maintenance_history if record.service_type == service_type]
        return max(services, key=lambda x: x.date_performed) if services else None
    
    async def _get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences for notifications and services"""
        return {
            "preferred_notification_time": "09:00",
            "max_travel_distance": 25,
            "budget_preference": "moderate",
            "preferred_shop_types": ["chain", "independent"]
        }
    
    async def _get_user_location(self, user_id: int) -> Dict:
        """Get user's location for finding nearby services"""
        # This would come from user profile or GPS
        return {
            "latitude": 41.5094,
            "longitude": -90.5789,  # Rock Island, IL
            "city": "Rock Island",
            "state": "IL"
        }
    
    async def _rank_mechanics(self, mechanics: List[Dict], service_type: str) -> List[Dict]:
        """Rank mechanics based on ratings, distance, specialization"""
        # Add ranking logic here
        return sorted(mechanics, key=lambda x: (x.get("rating", 0), -x.get("distance", 999)), reverse=True)
    
    def _format_mechanic_recommendations(self, mechanics: List[Dict]) -> str:
        """Format mechanic recommendations for user"""
        if not mechanics:
            return "I couldn't find any mechanics in your area right now."
        
        recommendations = []
        for i, mechanic in enumerate(mechanics, 1):
            rec = f"{i}. {mechanic.get('name', 'Unknown Shop')}"
            if mechanic.get('rating'):
                rec += f" ({mechanic['rating']}⭐)"
            if mechanic.get('distance'):
                rec += f" - {mechanic['distance']:.1f} miles away"
            recommendations.append(rec)
        
        return "\n".join(recommendations)
    
    async def _log_agent_action(self, action_type: str, user_id: int, car_id: int, data: Dict):
        """Log autonomous agent actions for monitoring and learning"""
        log_entry = {
            "timestamp": datetime.now(),
            "action_type": action_type,
            "user_id": user_id,
            "car_id": car_id,
            "data": data,
            "agent_version": "1.0"
        }
        # Store in database for analysis
        print(f"🤖 Agent Action: {action_type} for user {user_id}")

