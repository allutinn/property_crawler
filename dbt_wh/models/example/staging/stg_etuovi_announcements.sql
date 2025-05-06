-- models/stg_people.sql
{{ config(materialized='table') }}

with source as (
    select *
    FROM read_ndjson_auto('/app/data/raw/latest.ndjson')
)

select * from source