grammar pointers;

/*
* Parser Rules
*/

variable: VAR # variableName
          | NULL # nullvar;

statement: SKIPSTATEMENT # skip
    | variable ':=' ALLOC VAR # alloc
    | variable ':=' variable # assign
    | IF '(' cond=variable ')' '{' (ifs+=statement ';')+ '}' (ELSE '{' (elses+=statement ';')+ '}' )? # if
    | WHILE '(' cond=variable ')' '{' (statement ';')+ '}' # while
    ;
    
program: (statement ';')+
    ;


/*
 * Lexer Rules
 */
SKIPSTATEMENT       : 'skip';
ALLOC               : 'newObject';
IF                  : 'if';
THEN                : 'then';
ELSE                : 'else';
DONE                : 'done';
WHILE               : 'while';
DO                  : 'do';
OD                  : 'od';
NULL                : 'null';

VAR                 : [a-zA-Z] [._0-9A-Za-z]*;
INT                 : [0-9] +;

PLUS                : '+';
MINUS               : '-';
MULTIPLY            : '*';
DIVISION            : '/';

EQUALS              : '==';
LEQ                 : '<';

WHITESPACE          : [ \t\r\n\f]+ -> channel(HIDDEN);
