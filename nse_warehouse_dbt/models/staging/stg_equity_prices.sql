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