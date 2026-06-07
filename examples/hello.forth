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
    ." Hello, World!"
;

main
