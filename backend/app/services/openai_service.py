# app/services/openai_service.py
import openai
from typing import List, Dict, Optional
import json
import base64
from PIL import Image
import io

class OpenAIService:
    def __init__(self):
        self.client = openai.OpenAI()
        
    async def analyze_car_image(self, image_data: bytes, user_description: str = "") -> Dict:
        """Analyze car image for diagnostic purposes"""
        
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert automotive diagnostic assistant. Analyze car images and provide detailed diagnostic information. 
                
                Focus on:
                - Identifying visible issues or wear
                - Safety concerns
                - Maintenance recommendations
                - Estimated urgency (1-10)
                - Potential costs
                
                Return structured JSON response."""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Please analyze this car image. User description: {user_description}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ]
        
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-vision-preview",
            messages=messages,
            max_tokens=500
        )
        
        return self._parse_diagnostic_response(response.choices[0].message.content)
    
    async def generate_maintenance_recommendation(self, car_data: Dict, maintenance_history: List[Dict]) -> Dict:
        """Generate autonomous maintenance recommendations"""
        
        system_prompt = """You are CarBuddy, an autonomous car maintenance agent. Your role is to:
        
        1. Analyze car data and maintenance history
        2. Identify upcoming maintenance needs
        3. Prioritize recommendations by safety and cost
        4. Generate proactive suggestions
        5. Provide reasoning for each recommendation
        
        Be conversational but authoritative. Focus on preventing problems before they occur.
        
        Return JSON with structure:
        {
            "urgent_items": [...],
            "upcoming_items": [...],
            "preventive_suggestions": [...],
            "message_to_user": "Friendly personalized message"
        }
        """
        
        user_content = f"""
        Car Data: {json.dumps(car_data)}
        Maintenance History: {json.dumps(maintenance_history)}
        
        Please analyze and provide maintenance recommendations.
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    async def decide_autonomous_action(self, context: Dict) -> Dict:
        """Make autonomous decisions about what actions to take"""
        
        system_prompt = """You are an autonomous agent that makes decisions about car maintenance actions.
        
        Given the context, decide what autonomous actions to take:
        - Should we send a notification?
        - Should we research mechanics?
        - Should we schedule something?
        - What's the urgency?
        
        Be proactive but not pushy. Only take actions that clearly benefit the user.
        
        Return JSON:
        {
            "actions": [
                {
                    "type": "notification",
                    "priority": "high|medium|low",
                    "message": "...",
                    "timing": "immediate|within_24h|within_week"
                }
            ],
            "reasoning": "Why these actions were chosen"
        }
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context)}
            ],
            temperature=0.3  # Lower temperature for more consistent decisions
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    def _parse_diagnostic_response(self, response: str) -> Dict:
        """Parse and structure diagnostic response"""
        try:
            return json.loads(response)
        except:
            return {
                "analysis": response,
                "issues_found": [],
                "recommendations": [],
                "urgency": 5
            }
    
    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON response with fallback"""
        try:
            return json.loads(response)
        except:
            return {"error": "Failed to parse response", "raw": response}


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


# app/services/maps_service.py
import googlemaps
from typing import List, Dict, Optional
import os

class GoogleMapsService:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    
    async def find_nearby_mechanics(self, location: Dict, service_type: str = "car_repair", radius_miles: int = 25) -> List[Dict]:
        """Find nearby mechanics using Google Places API"""
        
        # Convert miles to meters
        radius_meters = radius_miles * 1609.34
        
        # Search for auto repair shops
        places_result = self.gmaps.places_nearby(
            location=(location['latitude'], location['longitude']),
            radius=radius_meters,
            type='car_repair',
            keyword=f'auto repair {service_type}'
        )
        
        mechanics = []
        for place in places_result.get('results', []):
            # Get additional details
            place_details = self.gmaps.place(
                place_id=place['place_id'],
                fields=['name', 'rating', 'formatted_phone_number', 'website', 'opening_hours', 'reviews']
            )
            
            detail = place_details.get('result', {})
            
            mechanic = {
                'place_id': place['place_id'],
                'name': place.get('name'),
                'rating': place.get('rating'),
                'price_level': place.get('price_level'),
                'address': place.get('vicinity'),
                'phone': detail.get('formatted_phone_number'),
                'website': detail.get('website'),
                'is_open': self._is_currently_open(detail.get('opening_hours')),
                'distance': self._calculate_distance(location, place['geometry']['location']),
                'reviews_summary': self._summarize_reviews(detail.get('reviews', []))
            }
            
            mechanics.append(mechanic)
        
        return mechanics
    
    def _is_currently_open(self, opening_hours: Optional[Dict]) -> bool:
        """Check if the business is currently open"""
        if not opening_hours:
            return False
        return opening_hours.get('open_now', False)
    
    def _calculate_distance(self, location1: Dict, location2: Dict) -> float:
        """Calculate distance between two points in miles"""
        import math
        
        lat1, lon1 = location1['latitude'], location1['longitude']
        lat2, lon2 = location2['lat'], location2['lng']
        
        # Haversine formula
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return round(distance, 1)
    
    def _summarize_reviews(self, reviews: List[Dict]) -> Dict:
        """Summarize recent reviews"""
        if not reviews:
            return {"summary": "No reviews available", "recent_rating": None}
        
        recent_reviews = reviews[:3]  # Get 3 most recent
        avg_rating = sum(r.get('rating', 0) for r in recent_reviews) / len(recent_reviews)
        
        return {
            "recent_rating": round(avg_rating, 1),
            "recent_count": len(recent_reviews),
            "summary": f"Recent average: {avg_rating:.1f}/5 from {len(recent_reviews)} reviews"
        }


# app/services/notification_service.py
from twilio.rest import Client
import os
from typing import Dict, List
import asyncio

class NotificationService:
    def __init__(self):
        self.twilio_client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
    
    async def send_push_notification(self, user_id: int, message: str, data: Dict = None):
        """Send push notification to user's device"""
        # Implementation would depend on your push notification service
        # (Firebase, APNs, etc.)
        
        notification_payload = {
            "user_id": user_id,
            "title": "CarBuddy Alert",
            "body": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # For now, just log the notification
        print(f"📱 Push Notification to user {user_id}: {message}")
        
        # In real implementation:
        # - Send to Firebase Cloud Messaging
        # - Handle device tokens
        # - Track delivery status
        
        return {"status": "sent", "notification_id": f"notif_{user_id}_{int(datetime.now().timestamp())}"}
    
    async def send_sms(self, phone_number: str, message: str):
        """Send SMS notification"""
        try:
            message = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=phone_number
            )
            
            print(f"📱 SMS sent to {phone_number}: {message.sid}")
            return {"status": "sent", "message_sid": message.sid}
            
        except Exception as e:
            print(f"❌ SMS failed to {phone_number}: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def send_email(self, email: str, subject: str, body: str):
        """Send email notification"""
        # Implementation would use your email service (SendGrid, SES, etc.)
        print(f"📧 Email to {email}: {subject}")
        return {"status": "sent"}
    
    async def schedule_notification(self, user_id: int, message: str, send_time: datetime):
        """Schedule a notification for later"""
        # This would integrate with your task queue (Celery)
        from app.tasks.maintenance_monitor import send_maintenance_reminder
        
        # Schedule the task
        send_maintenance_reminder.apply_async(
            args=[user_id, message],
            eta=send_time
        )
        
        return {"status": "scheduled", "send_time": send_time}


# app/tasks/celeryconfig.py
from datetime import timedelta

# Celery configuration
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
result_expires = timedelta(hours=1)
timezone = 'UTC'
enable_utc = True

# Beat schedule for autonomous agent
beat_schedule = {
    'autonomous-daily-maintenance-check': {
        'task': 'app.tasks.maintenance_monitor.autonomous_daily_check',
        'schedule': timedelta(hours=24),  # Run every 24 hours
        'options': {'expires': 3600}  # Task expires after 1 hour
    },
    'autonomous-hourly-urgent-check': {
        'task': 'app.tasks.maintenance_monitor.autonomous_urgent_check',
        'schedule': timedelta(hours=1),  # Check for urgent items every hour
        'options': {'expires': 1800}  # Task expires after 30 minutes
    },
    'weekly-agent-learning': {
        'task': 'app.tasks.maintenance_monitor.agent_learning_update',
        'schedule': timedelta(weeks=1),  # Weekly learning updates
        'options': {'expires': 7200}  # Task expires after 2 hours
    }
}


# app/tasks/maintenance_monitor.py (Updated)
from celery import Celery
from app.agents.autonomous_maintenance_agent import AutonomousMaintenanceAgent
import asyncio
from datetime import datetime

celery = Celery('carbuddy')
celery.config_from_object('app.tasks.celeryconfig')

@celery.task(bind=True, max_retries=3)
def autonomous_daily_check(self):
    """Main autonomous agent task - runs daily"""
    try:
        print(f"🤖 Starting autonomous daily check at {datetime.now()}")
        
        agent = AutonomousMaintenanceAgent()
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(agent.autonomous_daily_check())
        finally:
            loop.close()
        
        print("✅ Autonomous daily check completed successfully")
        return {"status": "completed", "timestamp": datetime.now().isoformat()}
        
    except Exception as exc:
        print(f"❌ Autonomous daily check failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery.task(bind=True)
def autonomous_urgent_check(self):
    """Check for urgent maintenance items every hour"""
    try:
        print(f"🚨 Urgent maintenance check at {datetime.now()}")
        
        agent = AutonomousMaintenanceAgent()
        
        # This would be a lighter check focusing only on safety-critical items
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Implementation for urgent-only checks
            pass  # Would call agent.autonomous_urgent_check()
        finally:
            loop.close()
        
        return {"status": "completed", "type": "urgent_check"}
        
    except Exception as exc:
        print(f"❌ Urgent check failed: {exc}")
        return {"status": "failed", "error": str(exc)}

@celery.task
def send_maintenance_reminder(user_id: int, car_id: int, message: str, service_type: str):
    """Send individual maintenance reminder"""
    try:
        from app.services.notfication_service import NotificationService
        
        notification_service = NotificationService()
        
        # Send the notification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                notification_service.send_push_notification(user_id, message)
            )
        finally:
            loop.close()
        
        print(f"✅ Maintenance reminder sent to user {user_id}")
        return result
        
    except Exception as e:
        print(f"❌ Failed to send maintenance reminder: {e}")
        return {"status": "failed", "error": str(e)}

@celery.task
def agent_learning_update():
    """Weekly task for agent to learn from user interactions"""
    try:
        print(f"🧠 Agent learning update started at {datetime.now()}")
        
        # This would analyze:
        # - Which recommendations users followed
        # - Which notifications were effective
        # - User feedback patterns
        # - Adjust agent behavior accordingly
        
        # For now, just log
        print("🧠 Agent learning analysis completed")
        
        return {"status": "completed", "learning_cycle": datetime.now().isoformat()}
        
    except Exception as e:
        print(f"❌ Agent learning update failed: {e}")
        return {"status": "failed", "error": str(e)}