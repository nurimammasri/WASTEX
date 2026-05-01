# WasteX Pipeline — Tasks Package
# Import semua task supaya bisa diakses dari main.py dengan mudah

from tasks.loader    import load_data, build_lookup_maps
from tasks.detection import (
    detect_type1, detect_type2, detect_type3, detect_type4, detect_type5,
    detect_type6, detect_type7, detect_type8, detect_type9, detect_type10,
)
from tasks.cleaning  import merge_anomalies, build_cleaned
from tasks.writer    import write_cleaned_sheets, write_validation_queue, write_automation_log
from tasks.notifier  import create_run_report, send_email_notification

__all__ = [
    "load_data", "build_lookup_maps",
    "detect_type1", "detect_type2", "detect_type3", "detect_type4", "detect_type5",
    "detect_type6", "detect_type7", "detect_type8", "detect_type9", "detect_type10",
    "merge_anomalies", "build_cleaned",
    "write_cleaned_sheets", "write_validation_queue", "write_automation_log",
    "create_run_report", "send_email_notification",
]
