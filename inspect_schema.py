from google.cloud import bigquery
from google.oauth2 import service_account
import os

key_path = 'service-account-key.json'
project_id = 'kleague-482106'
dataset_id = 'Kleague_db'
table_id = 'measurements'

try:
    # 1. Load Credentials
    creds = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(credentials=creds, project=creds.project_id)
    
    # 2. Get Table Schema
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    table = client.get_table(table_ref)
    
    print(f"✅ Table Schema for `{table_ref}`:")
    for i, field in enumerate(table.schema):
        print(f"  [Col {i}] {field.name} ({field.field_type})")

except Exception as e:
    print(f"❌ Error getting schema: {e}")
