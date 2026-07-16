with prices as (

    select *
    from {{ ref('stg_equity_prices') }}

),

calendar as (

    select *
    from {{ ref('dim_date') }}

),

final as (

    select
        p.TckrSymb as security_symbol,
        c.full_date as date_key,

        p.OpnPric as open_price,
        p.HghPric as high_price,
        p.LwPric as low_price,
        p.ClsPric as close_price,
        p.TtlTradgVol as total_volume,
        p.TtlTrfVal as total_turnover,
        p.TtlNbOfTxsExctd as total_trades,

        c.is_weekend,
        c.day_of_week,
        c.month_name,
        c.quarter,
        c.year

    from prices p
    left join calendar c
        on p.trade_date = c.full_date

)

select * from final