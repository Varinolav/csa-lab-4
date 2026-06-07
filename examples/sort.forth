variable cnt
variable i variable j variable mi variable tmp
variable buf  15 alloc

: a@      buf + load ;
: a!      buf + store ;

: read-num
    0
    begin
        0 in
        dup 47 >
    while
        48 - swap 10 * +
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

: newline
    10 1 out
;

: read-array
    read-num cnt store
    0 i store
    begin
        i load cnt load <
    while
        read-num i load a!
        i load 1 + i store
    repeat
;

: sort-array
    0 i store
    begin
        i load cnt load 1 - <
    while
        i load mi store
        i load 1 + j store
        begin
            j load cnt load <
        while
            j load a@ mi load a@ <
            if
                j load mi store
            then
            j load 1 + j store
        repeat

        i load a@ tmp store
        mi load a@ i load a!
        tmp load mi load a!
        i load 1 + i store
    repeat
;

: print-array
    0 i store
    begin
        i load cnt load <
    while
        i load a@ print-int
        i load cnt load 1 - <
        if
            32 1 out
        then
        i load 1 + i store
    repeat
    newline
;

: main
    read-array
    sort-array
    print-array
;

main
