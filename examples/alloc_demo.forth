variable len = 5
variable i
variable buf  4 alloc

: a@      buf + load ;
: a!      buf + store ;

: print-int
    dup 0 =
    if   48 1 out
    else
        dup 10 /
        dup 0 >  if  print-int  else  drop  then
        10 mod 48 + 1 out
    then
;

: nl   10 1 out ;

: fill
    0 i store
    begin  i load len load <  while
        i load 1 +  dup *  i load a!
        i load 1 + i store
    repeat
;

: sum
    0  0 i store
    begin  i load len load <  while
        i load a@ +
        i load 1 + i store
    repeat
;

: main
    fill
    sum print-int nl
;
main
