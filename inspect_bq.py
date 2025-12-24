from google.cloud import bigquery
from google.oauth2 import service_account
import os

key_path = 'service-account-key.json'

if not os.path.exists(key_path):
    print("❌ Error: service-account-key.json not found.")
    exit()

try:
    # 1. Load Credentials
    creds = service_account.Credentials.from_service_account_file(key_path)
    project_id = creds.project_id
    print(f"✅ Authenticated as: {creds.service_account_email}")
    print(f"🔑 Key Origin Project ID: {project_id}")
    
    # 2. Connect to BigQuery
    client = bigquery.Client(credentials=creds, project=project_id)
    
    # 3. List Datasets in the Origin Project
    print(f"\n🔍 Searching for datasets in '{project_id}'...")
    datasets = list(client.list_datasets())
    
    if datasets:
        print(f"🎉 Found {len(datasets)} dataset(s):")
        for dataset in datasets:
            print(f"  - {dataset.dataset_id} (Full ID: {dataset.full_dataset_id})")
    else:
        print("⚠️  No datasets found in this project.")
        
except Exception as e:
    print(f"\n❌ Error Occurred:\n{str(e)}")
