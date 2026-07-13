with date_spine as (

    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2025-01-01' as date)",
        end_date="cast('2028-01-01' as date)"
    ) }}

),

final as (

    select
        date_day as full_date,
        EXTRACT(DAYOFWEEK from date_day) as day_of_week_num,
        FORMAT_DATE('%A', date_day) as day_of_week,
        EXTRACT(DAY from date_day) as day_of_month,
        EXTRACT(MONTH from date_day) as month_num,
        FORMAT_DATE('%B', date_day) as month_name,
        EXTRACT(QUARTER from date_day) as quarter,
        EXTRACT(YEAR from date_day) as year,
        case when EXTRACT(DAYOFWEEK from date_day) in (1,7) then true else false end as is_weekend

    from date_spine

)

select * from final