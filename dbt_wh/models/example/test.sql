-- models/stg_people.sql
{{ config(materialized='table') }}

with source as (
    select *
    from read_csv_auto('/app/data/raw/example_data.csv', header=true)
),

casted as (
    select
        cast(id as integer) as id,
        cast(name as varchar) as name,
        cast(value as integer) as value
    from source
)

select * from casted
