variable counter

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

: main
    7 counter store
    counter load
    print-int newline
    ." Harvard"
    newline
;

main
