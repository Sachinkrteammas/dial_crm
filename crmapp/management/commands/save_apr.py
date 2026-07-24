import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from crmapp.services import save_apr_report

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pull the VICIdial Agent Time Detail report and save it to the DB. Defaults to yesterday."

    def add_arguments(self, parser):
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        parser.add_argument("--start-date", default=yesterday, help="YYYY-MM-DD, default: yesterday")
        parser.add_argument("--end-date", default=yesterday, help="YYYY-MM-DD, default: yesterday")

    def handle(self, *args, **options):
        start_date = options["start_date"]
        end_date = options["end_date"]
        try:
            count = save_apr_report(start_date, end_date)
        except Exception as exc:
            logger.exception("APR save failed for %s to %s", start_date, end_date)
            raise CommandError(f"APR save failed: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Saved {count} agent rows for {start_date} to {end_date}"
        ))