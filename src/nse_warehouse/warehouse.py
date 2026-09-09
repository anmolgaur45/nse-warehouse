import json
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import datetime


def load_schema(path: str) -> list[bigquery.SchemaField]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    schema_field = [bigquery.SchemaField.from_api_repr(field) for field in data]
    return schema_field

def ensure_table(
        client: bigquery.Client,
        table_id: str,
        schema: list[bigquery.SchemaField],
        partition_field: str | None = None,
        clustering_fields: list[str] | None = None,
        expires_in_hours: int | None = None
) -> bigquery.Table:

    try:
        table = client.get_table(table_id)
    except NotFound:
        print(f"Table {table_id} not found. Creating it now...")

        table = bigquery.Table(table_id, schema=schema)

        if partition_field:
            table.time_partitioning = bigquery.TimePartitioning(
                field=partition_field,
                type_=bigquery.TimePartitioningType.DAY,
            )

        if clustering_fields:
            table.clustering_fields = clustering_fields

        if expires_in_hours:
            table.expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=expires_in_hours)

        return client.create_table(table)

    else:
        existing_schema = {
            (f.mode, f.name, f.field_type) for f in table.schema
        }
        expected_schema = {
            (f.mode, f.name, f.field_type) for f in schema
        }
        if existing_schema != expected_schema:
            missing_in_existing = expected_schema - existing_schema
            extra_in_existing = existing_schema - expected_schema

            error_msg = f"Schema mismatch for table {table_id}!\n"

            if missing_in_existing:
                error_msg += f"Missing fields: {missing_in_existing}\n"
            if extra_in_existing:
                error_msg += f"Unexpected fields found: {extra_in_existing}\n"

            raise ValueError(error_msg)

        return table