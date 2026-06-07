: base   65536 65536 * ;

: a-hi   1 ;
: a-lo   40000 100000 * ;
: b-hi   2 ;
: b-lo   10000 100000 * ;

variable r-hi variable r-lo

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

: add64
    a-lo b-lo +
    carry
    swap r-lo store
    a-hi b-hi + +
    r-hi store
;

: print64
    swap base * +
    print-int
;

: main
    ." A = " a-hi a-lo print64 newline
    ." B = " b-hi b-lo print64 newline

    add64

    ." A+B = " r-hi load r-lo load print64 newline
    ." A+B words  = "
    r-hi load print-int 32 1 out
    r-lo load print-int newline
;

main
