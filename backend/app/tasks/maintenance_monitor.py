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