with security_days as (

    select
        TckrSymb,
        trade_date,
        FinInstrmNm,
        ISIN
    from {{ ref('stg_equity_prices') }}

),

with_previous_values as (

    select
        *,
        lag(FinInstrmNm) over (
            partition by TckrSymb
            order by trade_date
        ) as prev_name,

        lag(ISIN) over (
            partition by TckrSymb
            order by trade_date
        ) as prev_isin

    from security_days

),

change_flags as (

    select
        *,
        case
            when (prev_name is not null and prev_name != FinInstrmNm)
            or (prev_isin is not null and prev_isin != ISIN) then 1
            else 0
        end as is_new_version

    from with_previous_values

),

versioned as (

    select
        *,
        sum(is_new_version) over (
            partition by TckrSymb
            order by trade_date
        ) as version_num

    from change_flags

),

collapsed as (

    select
        TckrSymb,
        version_num,
        ANY_VALUE(FinInstrmNm) as security_name,
        ANY_VALUE(ISIN) as isin,

        min(trade_date) as valid_from,
        max(trade_date) as valid_to

    from versioned
    group by TckrSymb, version_num

),

with_next_version as (

    select
        *,
        lead(valid_from) over (
            partition by TckrSymb order by version_num
        ) as next_valid_from

    from collapsed

),

with_end_dates as (

    select
        *,
        case
            when next_valid_from is not null
            then DATETIME_SUB(next_valid_from, interval 1 day)
            else null
        end as corrected_valid_to

    from with_next_version

)

select
    {{ dbt_utils.generate_surrogate_key(['TckrSymb', 'version_num']) }} as security_key,
    TckrSymb as security_symbol,
    security_name,
    isin,
    valid_from,
    corrected_valid_to as valid_to
from with_end_dates