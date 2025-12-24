from google.cloud import bigquery
from google.oauth2 import service_account
import os

key_path = 'service-account-key.json'
project_id = 'kleague-482106'
dataset_id = 'Kleague_db'
table_id = 'measurements'

def get_field_type(field):
    # Test_ID만 STRING으로 강제 변환
    if field.name == 'Test_ID':
        return 'STRING'
    return field.field_type

try:
    creds = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(credentials=creds, project=creds.project_id)
    
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    table = client.get_table(table_ref)
    
    # 1. 스키마 생성
    schema_list = []
    for field in table.schema:
        schema_list.append(f"  {field.name} {get_field_type(field)}")
    schema_str = ",\n".join(schema_list)
    
    # 2. 소스 URI 추출
    # External Config 확인
    ext_config = table.external_data_configuration
    if not ext_config:
        print("❌ This is not an external table.")
        exit()
        
    source_uris = ext_config.source_uris
    if not source_uris:
        print("❌ No source URIs found.")
        exit()
        
    uri_str = f"['{source_uris[0]}']"
    
    # 3. SQL 생성
    sql = f"""
CREATE OR REPLACE EXTERNAL TABLE `{project_id}.{dataset_id}.{table_id}`
(
{schema_str}
)
OPTIONS (
  format = 'GOOGLE_SHEETS',
  uris = {uri_str},
  skip_leading_rows = 1
);
"""
    print(sql)

except Exception as e:
    print(f"❌ Error: {e}")
