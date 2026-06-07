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

: sum-to-n
    0 swap
    begin
        dup 0 >
    while
        swap over + swap
        1 -
    repeat
    drop
;

: print-int
    dup 0 =
    if
        48 1 out
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
    print-int
    10 1 out
;

: main
    read-int
    sum-to-n
    print-line
;

main
