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

: double
    2 *
;

: main
    21 double print-int newline
    21 ' double execute print-int newline
;

main
