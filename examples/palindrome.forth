variable max-prod
variable hi
variable lo
variable i
variable j
variable rev-acc
variable pow-acc

: read-int
    0
    begin
        0 in
        dup 10 =
        0 =
    while
        48 -
        swap 10 * +
    repeat
    drop
;

: print-int
    dup 0 =
    if
        drop
    else
        dup 10 /
        dup 0 >
        if
            print-int
        else
            drop
        then
        10 mod
        48 + 1 out
    then
;

: print-line
    dup 0 =
    if drop 48 1 out
    else print-int
    then
    10 1 out
;

: pow10
    1 pow-acc store
    begin
        dup 0 >
    while
        pow-acc load 10 * pow-acc store
        1 -
    repeat
    drop
    pow-acc load
;

: reverse
    0 rev-acc store
    begin
        dup 0 >
    while
        rev-acc load 10 *
        over 10 mod +
        rev-acc store
        10 /
    repeat
    drop
    rev-acc load
;

: palindrome?
    dup reverse =
;

: main
    read-int
    dup pow10 hi store
    1 - pow10 lo store
    0 max-prod store

    lo load i store
    begin
        i load hi load <
    while
        i load j store
        begin
            j load hi load <
        while
            i load j load *
            dup palindrome?
            over max-prod load >
            *
            if max-prod store
            else drop
            then
            j load 1 + j store
        repeat
        i load 1 + i store
    repeat

    max-prod load print-line
;

main
