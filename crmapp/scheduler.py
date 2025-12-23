from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from .cron import fetch_lead_status_job

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run every hour
    # scheduler.add_job(fetch_lead_status_job, 'interval', hours=1, id='fetch_lead_status')
    scheduler.add_job(fetch_lead_status_job, 'interval', minutes=10, id='fetch_lead_status', replace_existing=True)
    scheduler.start()
    print("✅ APScheduler started successfully")
