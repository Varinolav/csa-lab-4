: newline
    10 1 out
;

: main
    ." What is your name?" newline
    ." Hello, "
    begin
        0 in
        dup 10 =
        0 =
    while
        1 out
    repeat
    drop
    ." !" newline
;

main
