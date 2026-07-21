with security_versions as (

    select *
    from {{ ref('dim_security') }}

),

self_joined as (

    select
        a.security_symbol,
        a.security_key as key_a,
        a.valid_from as a_start,
        a.valid_to as a_end,
        b.security_key as key_b,
        b.valid_from as b_start,
        b.valid_to as b_end

    from security_versions a
    join security_versions b
        on a.security_symbol = b.security_symbol
        and a.security_key < b.security_key

    where
        a.valid_from <= coalesce(b.valid_to, cast('2099-12-31' as datetime))
        and b.valid_from <= coalesce(a.valid_to, cast('2099-12-31' as datetime))

)

select * from self_joined