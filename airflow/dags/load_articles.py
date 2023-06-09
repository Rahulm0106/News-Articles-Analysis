import os
import pyarrow.csv as pv
import pyarrow.parquet as pq
import pandas as pd
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateExternalTableOperator


from google.cloud import storage

default_args = {
    'owner': 'airflow'
}

AIRFLOW_HOME = os.environ.get('AIRFLOW_HOME', '/opt/airflow')


URL = 'https://www.dropbox.com/s/cn2utnr5ipathhh/all-the-news-2-1.zip'

# FILE = "{{ execution_date.strftime(\'%Y-%m-%d-%-H\') }}.json.gz"
# UNZIP_FILE = "{{ execution_date.strftime(\'%Y-%m-%d-%-H\') }}.json"

CSV_FILENAME = 'all-the-news-2-1.csv'
ZIP_FILENAME = 'articles.zip'
PARQUET_FILENAME = CSV_FILENAME.replace('csv', 'parquet')
DATA_FOLDER = 'data_airflow'

CSV_OUTFILE = f'{AIRFLOW_HOME}/{CSV_FILENAME}'
ZIP_OUTFILE = f'{AIRFLOW_HOME}/{ZIP_FILENAME}'
PARQUET_OUTFILE = f'{AIRFLOW_HOME}/{PARQUET_FILENAME}'
ARTICLE_DATA = f'{AIRFLOW_HOME}/{DATA_FOLDER}'
TABLE_NAME = 'articles'

GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID')
GCP_GCS_BUCKET = os.environ.get('GCP_GCS_BUCKET')
# BIGQUERY_DATASET = os.environ.get('BIGQUERY_DATASET', 'streamify_stg')


def convert_to_parquet(csv_file, parquet_file):
    if not csv_file.endswith('csv'):
        raise ValueError('The input file is not in csv format')

    # Path(f'{AIRFLOW_HOME}/fhv_tripdata/parquet').mkdir(parents=True, exist_ok=True)

    table = pd.read_csv("all-the-news-2-1.csv", iterator=True, chunksize=100000)
    i = 0
    while True:
        i = i + 1
        try:
                
            df = next(table)
            print(str(i) + "_data.parquet")
            Data_Home = DATA_FOLDER + "/" + str(i) + "_data.parquet"
            # path = Path(f"data/{color}/{dataset_file}.parquet")
            # path = Path(f"{Data_HOME}/{str(i) + "_data.parquet"}")
            df.to_parquet(Data_Home)

        except StopIteration:
            print("Finished converting data into the parquet format")
            break

def upload_to_gcs(file_path, bucket_name, blob_name):
    """
    Upload the downloaded file to GCS
    """
    # WORKAROUND to prevent timeout for files > 6 MB on 800 kbps upload speed.
    # (Ref: https://github.com/googleapis/python-storage/issues/74)

    # storage.blob._MAX_MULTIPART_SIZE = 5 * 1024 * 1024  # 5 MB
    # storage.blob._DEFAULT_CHUNKSIZE = 5 * 1024 * 1024  # 5 MB

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)


with DAG(
    dag_id=f'load_articles_dag',
    default_args=default_args,
    description=f'Download and Ingest data to Google Cloud Storage',
    schedule_interval="@once",  # At the 5th minute of every hour
    start_date=datetime(2023,4,16),
    catchup=False,
    # max_active_runs=3,
    tags=['articles_data']
) as dag:

    new_folder_creation_task = BashOperator(
        task_id="new_folder_creation",
        bash_command=f"mkdir {ARTICLE_DATA}"
    )

    download_articles_file_task = BashOperator(
        task_id="download_articles_file",
        bash_command=f"curl -sSLf {URL} > {ZIP_OUTFILE}"
    )

    unzip_articles_file_task = BashOperator(
        task_id="unzip_articles_file",
        bash_command=f"unzip {ZIP_OUTFILE} -d {AIRFLOW_HOME}"
    )

    convert_to_parquet_task = PythonOperator(
        task_id='convert_to_parquet',
        python_callable=convert_to_parquet,
        op_kwargs={
            'csv_file': CSV_OUTFILE,
            'parquet_file': PARQUET_OUTFILE
        }
    )

    upload_to_gcs_task = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_to_gcs,
        op_kwargs={
            'file_path': DATA_FOLDER,
            'bucket_name': GCP_GCS_BUCKET,
            'blob_name': f'{DATA_FOLDER}'
        }
    )
    
    remove_files_from_local_task = BashOperator(
        task_id='remove_files_from_local',
        bash_command=f'rm {CSV_OUTFILE} {ZIP_OUTFILE}'
    )

    new_folder_creation_task >> download_articles_file_task >> unzip_articles_file_task >> convert_to_parquet_task >> upload_to_gcs_task >> remove_files_from_local_task
