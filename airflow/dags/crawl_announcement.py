from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='crawl_announcements_only',
    start_date=datetime.now(),
    schedule_interval=None,
    catchup=False,
) as dag:

    crawl_announcements = BashOperator(
        task_id='crawl_announcements',
        bash_command='set -e; docker exec extractor python -u etuovi_crawler/crawl_announcement.py',
        do_xcom_push=True,
        env={"PYTHONUNBUFFERED": "1"}
    )