{{ config(materialized='table') }}


{% set data_date = var('data_date', none) %}

{% set file_path = '/app/data/raw/' ~ data_date ~ '/' ~ data_date ~ '.ndjson' if data_date else '/app/data/raw/latest.ndjson' %}

with source as (
    select 
        {% if data_date %} DATE '{{ data_date }}' {% else %} CURRENT_DATE {% endif %} as data_date,
        *
    from read_ndjson_auto('{{ file_path }}')
)

select * from source
