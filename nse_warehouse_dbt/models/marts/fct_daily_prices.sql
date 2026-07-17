with prices as (

    select *
    from {{ ref('stg_equity_prices') }}

),

calendar as (

    select *
    from {{ ref('dim_date') }}

),

security_dim as (

    select *
    from {{ ref('dim_security') }}

),

final as (

    select
        p.TckrSymb as security_symbol,
        sd.security_key,
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
    left join security_dim sd
        on p.TckrSymb = sd.security_symbol
        and p.trade_date between sd.valid_from and coalesce(sd.valid_to, cast('2099-12-31' as datetime))

)

select * from final