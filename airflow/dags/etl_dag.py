from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {
    'start_date': datetime(2024, 1, 1),
    'retries': 0,
}

with DAG(
    dag_id='extract_then_dbt',
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    extract = BashOperator(
        task_id='run_extractor',
        bash_command='docker exec extractor python test_extract.py',
        do_xcom_push=True
    )

    transform = BashOperator(
        task_id='run_dbt',
        bash_command='docker exec dbt-wh dbt run',
        do_xcom_push=True
    )

    extract >> transform
