from framework.base import ETLTask, ETLJob
from framework.registry import register_job
from framework.context import ETLContext

class ExtractOrdersTask(ETLTask):
    name = "extract"

    def execute(self, context: ETLContext):
        # Retrieve input records or use defaults
        records = context.parameters.get("records")
        if not records:
            records = [
                {"order_id": "ord_101", "customer": "Alice", "amount": "149.50", "currency": "usd", "email": "ALICE@EXAMPLE.COM"},
                {"order_id": "ord_102", "customer": "Bob", "amount": "210.00", "currency": "eur", "email": "bob@example.com"},
                {"order_id": "ord_103", "customer": "Charlie", "amount": "85.25", "currency": "USD", "email": "CHARLIE@COMPANY.ORG"},
                {"order_id": "ord_104", "customer": "BadRow", "amount": "-15.00", "currency": "usd", "email": "bad_email_format"}
            ]

        raw_key = f"raw/{context.job_id}/orders.json"
        s3_uri = context.save_s3(raw_key, {"job_id": context.job_id, "orders": records}, bucket_type="raw")
        context.record_metric("extracted_records_count", len(records))

        return {
            "raw_s3_key": raw_key,
            "raw_s3_uri": s3_uri,
            "extracted_count": len(records)
        }

class CleanseOrdersTask(ETLTask):
    name = "transform"

    def execute(self, context: ETLContext):
        raw_key = context.get("raw_s3_key")
        payload = context.read_s3(raw_key, bucket_type="raw")
        orders = payload.get("orders", [])

        valid_orders = []
        rejected_orders = []

        for o in orders:
            try:
                amt = float(o.get("amount", 0))
                email = str(o.get("email", "")).strip().lower()
                curr = str(o.get("currency", "USD")).strip().upper()

                if amt > 0 and "@" in email:
                    valid_orders.append({
                        "order_id": o.get("order_id"),
                        "customer": o.get("customer"),
                        "amount": round(amt, 2),
                        "currency": curr,
                        "email": email
                    })
                else:
                    rejected_orders.append({"record": o, "reason": "Invalid amount or email format"})
            except Exception as e:
                rejected_orders.append({"record": o, "reason": str(e)})

        processed_key = f"processed/{context.job_id}/clean_orders.json"
        s3_uri = context.save_s3(
            processed_key,
            {
                "job_id": context.job_id,
                "valid_count": len(valid_orders),
                "rejected_count": len(rejected_orders),
                "orders": valid_orders,
                "rejected": rejected_orders
            },
            bucket_type="processed"
        )

        context.record_metric("valid_count", len(valid_orders))
        context.record_metric("rejected_count", len(rejected_orders))

        return {
            "processed_s3_key": processed_key,
            "processed_s3_uri": s3_uri,
            "valid_count": len(valid_orders),
            "rejected_count": len(rejected_orders)
        }

class LoadSummaryTask(ETLTask):
    name = "load"

    def execute(self, context: ETLContext):
        processed_key = context.get("processed_s3_key")
        data = context.read_s3(processed_key, bucket_type="processed")
        orders = data.get("orders", [])

        total_revenue = sum(o["amount"] for o in orders)
        context.record_metric("total_revenue", total_revenue)

        return {
            "status": "COMPLETED",
            "total_revenue": round(total_revenue, 2),
            "processed_orders_count": len(orders)
        }

@register_job("customer_orders")
class CustomerOrdersJob(ETLJob):
    description = "Ingests customer order transactions, cleans schemas, and calculates totals"
    tasks = [
        ExtractOrdersTask(),
        CleanseOrdersTask(),
        LoadSummaryTask()
    ]
