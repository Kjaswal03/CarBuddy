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

