from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, time

from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowSkipException


def skip_blackout_hours(**context):
    now = datetime.now().time()
    if now >= time(22, 0) or now < time(6, 0):
        raise AirflowSkipException("❌ Skipping DAG run during blackout window (22:00–06:00).")




with DAG(
    dag_id='fetch_links_and_crawl_apartments',
    start_date=datetime.now(),
    schedule_interval="*/5 * * * *",  # every 5 mins
    catchup=False,
    max_active_runs=1,                # ⬅️ blocks overlap
) as dag:

    skip_task = PythonOperator(
        task_id="check_time_window",
        python_callable=skip_blackout_hours,
    )

    crawl_all_links = BashOperator(
        task_id='crawl_all_links',
        bash_command='set -e; docker exec extractor python -u etuovi_crawler/crawl_all_links.py',
        do_xcom_push=True,
        env={"PYTHONUNBUFFERED": "1"}
    )

    crawl_announcements = BashOperator(
        task_id='crawl_announcements',
        bash_command='set -e; docker exec extractor python -u etuovi_crawler/crawl_announcement.py',
        do_xcom_push=True,
        env={"PYTHONUNBUFFERED": "1"}
    )

    update_latest_ndjson = BashOperator(
        task_id='update_latest_ndjson',
        bash_command='set -e; docker exec extractor python -u etuovi_crawler/update_latest_ndjson.py',
    )

    skip_task >> crawl_all_links >> crawl_announcements >> update_latest_ndjson
