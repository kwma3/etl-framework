from framework.base import ETLTask, ETLJob
from framework.registry import register_job
from framework.context import ETLContext

class ExtractUserActivityTask(ETLTask):
    name = "extract"

    def execute(self, context: ETLContext):
        events = context.parameters.get("events")
        if not events:
            events = [
                {"event_id": "evt_01", "user_id": "usr_alice", "status": "SUCCESS", "ip": "192.168.1.42", "device": "mobile"},
                {"event_id": "evt_02", "user_id": "usr_bob", "status": "FAILED", "ip": "10.0.0.15", "device": "desktop"},
                {"event_id": "evt_03", "user_id": "usr_bob", "status": "FAILED", "ip": "10.0.0.15", "device": "desktop"},
                {"event_id": "evt_04", "user_id": "usr_charlie", "status": "SUCCESS", "ip": "172.16.0.8", "device": "tablet"}
            ]

        raw_key = f"raw/{context.job_id}/user_activity.json"
        s3_uri = context.save_s3(raw_key, {"job_id": context.job_id, "events": events}, bucket_type="raw")
        context.record_metric("extracted_events_count", len(events))

        return {
            "raw_s3_key": raw_key,
            "raw_s3_uri": s3_uri,
            "extracted_count": len(events)
        }

class AnonymizeAndFilterTask(ETLTask):
    name = "transform"

    def execute(self, context: ETLContext):
        raw_key = context.get("raw_s3_key")
        payload = context.read_s3(raw_key, bucket_type="raw")
        events = payload.get("events", [])

        processed_events = []
        failed_count = 0
        success_count = 0

        for ev in events:
            # Mask IP address for privacy: 192.168.1.42 -> 192.168.1.xxx
            ip = ev.get("ip", "0.0.0.0")
            parts = ip.split(".")
            masked_ip = ".".join(parts[:3] + ["xxx"]) if len(parts) == 4 else "xxx.xxx.xxx.xxx"

            status = ev.get("status", "UNKNOWN").upper()
            if status == "FAILED":
                failed_count += 1
            elif status == "SUCCESS":
                success_count += 1

            processed_events.append({
                "event_id": ev.get("event_id"),
                "user_id": ev.get("user_id"),
                "status": status,
                "masked_ip": masked_ip,
                "device": ev.get("device", "unknown").lower()
            })

        processed_key = f"processed/{context.job_id}/clean_activity.json"
        s3_uri = context.save_s3(
            processed_key,
            {
                "job_id": context.job_id,
                "total_events": len(processed_events),
                "success_count": success_count,
                "failed_count": failed_count,
                "events": processed_events
            },
            bucket_type="processed"
        )

        context.record_metric("success_count", success_count)
        context.record_metric("failed_count", failed_count)

        return {
            "processed_s3_key": processed_key,
            "processed_s3_uri": s3_uri,
            "success_count": success_count,
            "failed_count": failed_count
        }

class AggregateActivityTask(ETLTask):
    name = "load"

    def execute(self, context: ETLContext):
        processed_key = context.get("processed_s3_key")
        data = context.read_s3(processed_key, bucket_type="processed")
        events = data.get("events", [])

        unique_users = len(set(ev["user_id"] for ev in events))
        context.record_metric("unique_active_users", unique_users)

        return {
            "status": "COMPLETED",
            "unique_active_users": unique_users,
            "total_events_processed": len(events)
        }

@register_job("user_activity")
class UserActivityJob(ETLJob):
    description = "Ingests user login activity, masks IP addresses, and aggregates active users"
    tasks = [
        ExtractUserActivityTask(),
        AnonymizeAndFilterTask(),
        AggregateActivityTask()
    ]
