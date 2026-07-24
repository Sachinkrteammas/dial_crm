# services.py
from datetime import datetime
from django.db import transaction
from django.utils.dateparse import parse_date
import requests

from .models import AgentTimeDetailReport
from .views import _fetch_apr_csv, _parse_apr_csv  # reuse what already works


def save_apr_report(start_date: str, end_date: str) -> int:
    start_date_obj = parse_date(start_date)
    end_date_obj = parse_date(end_date)
    if not start_date_obj or not end_date_obj:
        raise ValueError(f"Invalid date(s): start_date={start_date!r}, end_date={end_date!r}")

    csv_text = _fetch_apr_csv(start_date, end_date)
    records = list(_parse_apr_csv(csv_text))

    with transaction.atomic(using="default"):
        AgentTimeDetailReport.objects.using("default").filter(
            report_date_start=start_date_obj,
            report_date_end=end_date_obj,
        ).delete()

        objs = [
            AgentTimeDetailReport(
                report_date_start=start_date_obj,
                report_date_end=end_date_obj,
                **record,
            )
            for record in records
        ]
        AgentTimeDetailReport.objects.using("default").bulk_create(objs)
        return len(objs)