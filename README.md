## Set up and Installation.

To use the antlr framework we need the ANTLR code generation tool itself and a runtime library for python.

Installation steps

1.  The code generation part of ANTLR requires java. Install java on your machine.
2.  Install  the  ANTLR  runtime  for  python3.You  can  use  the  command `python3 -m pip install antlr4-python3-runtime`. 
More   instructions   are   available   at https://github.com/antlr/antlr4/blob/master/doc/python-target.md.
3.  Install   the   other   required   python   packages   for   visualizing   the   CFG.   Use `apt-get install libgraphviz-dev` to  install graphviz and  then  use  the  command `python3 -m pip install networkx pygraphviz` to install the python packages required.
4.  Run the./build.sh script to generate the parser/lexer code.

This is the first time we are using this code base. Thank you for your patience while we figure
out all the problems in the code.
