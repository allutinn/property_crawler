from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='crawl_links_fixed',
    start_date= datetime.now(),
    schedule_interval=None,
    catchup=False,
) as dag:

    crawl_all_links = BashOperator(
        task_id='crawl_links_fixed',
        bash_command='docker exec -e ETUOVI_LAST_PAGE=10 extractor python -u etuovi_crawler/crawl_all_links.py',
        do_xcom_push=True,
        env={"PYTHONUNBUFFERED": "1"}
    )