#!/bin/bash
for testfile in test1 test2 test3 test4 test5 test6 test7
do
    python3 parser.py tests/$testfile.c > temp.out
    if cmp --silent -- temp.out tests/$testfile.output.correct; then
        echo "$testfile: PASS"
    else
        echo "$testfile: FAIL"
        diff temp.out tests/$testfile.output.correct
    fi
done














