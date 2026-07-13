-- Staging model: cleaned, deduplicated, EQ-only equity bhavcopy.
-- Grain: one row per (trade_date, symbol).
--
-- Job of this model (and only this):
--   1. select from the raw source
--   2. filter to SctySrs = 'EQ'
--   3. dedupe re-ingested days via ROW_NUMBER() over ingestion_timestamp
-- NOT this model's job: renaming every column, building dims/facts, joins.
-- Keep it close to 1:1 with the raw source -- light cleaning only.

with source as (

    select *
    from {{ source('raw', 'equity_bhavcopy') }}

),

filtered as (

    select *
    from source
    where SctySrs = 'EQ'

),

deduped as (

    select
        *,
        row_number() over (
            partition by trade_date, TckrSymb
            order by ingestion_timestamp desc
        ) as row_num

    from filtered

)

select
    * except (row_num)  -- drop the helper column, it's not real data
from deduped
where row_num = 1