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

: newline
    10 1 out
;

: emit-str
    dup load
    swap 1 +
    swap
    begin
        dup 0 >
    while
        over load
        1 out
        swap 1 + swap
        1 -
    repeat
    drop drop
;

: main
    s" Forth"
    dup load
    print-int newline
    emit-str newline
;

main
