grammar pointers;

/*
* Parser Rules
*/

variable: VAR # variableName
    ;

booleanExpression: INT
    | expression EQUALS expression
    | expression LEQ expression
    ;

expression: INT # literal
    | variable # variableExpr
    | '(' expression ')' # paran
    | expression MULTIPLY expression # multiply
    | expression DIVISION expression # divide
    | expression PLUS expression # add
    | expression MINUS expression # minus
    ;

statement: SKIPSTATEMENT # skip
    | variable '=' expression # assign
    | IF cond=expression '{' (ifs+=statement ';')+ '}' (ELSE '{' (elses+=statement ';')+ '}' )? # if
    | WHILE '(' cond=expression ')' '{' (statement ';')+ '}' # while
    ;
    
program: (statement ';')+
    ;


/*
 * Lexer Rules
 */
SKIPSTATEMENT       : 'skip';
MALLOC              : 'malloc';
IF                  : 'if';
THEN                : 'then';
ELSE                : 'else';
DONE                : 'done';
WHILE               : 'while';
DO                  : 'do';
OD                  : 'od';

VAR                 : [a-zA-Z] [._0-9A-Za-z]*;
INT                 : [0-9] +;

PLUS                : '+';
MINUS               : '-';
MULTIPLY            : '*';
DIVISION            : '/';

EQUALS              : '==';
LEQ                 : '<';

WHITESPACE          : [ \t\r\n\f]+ -> channel(HIDDEN);
