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

: sum-of-squares
    0 swap
    begin
        dup 0 >
    while
        swap over
        dup *
        +
        swap
        1 -
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
    if
        drop 48 1 out
    else
        print-int
    then
    10 1 out
;

: main
    read-int
    dup sum-to-n
    dup *
    swap sum-of-squares
    -
    print-line
;

main
