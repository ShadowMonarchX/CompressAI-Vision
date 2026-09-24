from app.config import settings
from app.services.jobs import jobs
def get_settings(): return settings
def get_job_store(): return jobs
