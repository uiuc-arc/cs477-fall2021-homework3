import sys
from antlr4 import CommonTokenStream
from antlr4 import InputStream
from pointersLexer import pointersLexer
from pointersParser import pointersParser
from pointersVisitor import pointersVisitor
from pointersListener import pointersListener
from antlr4 import ParseTreeWalker
import networkx as nx

import operator


# This class holds the data for a Control Flow Graph node
# content - the code for the node
# text    - is a textual representation
# isSplit - denotes whether the CFG node is splitting the execution (start of a loop, conditional)
# bbid    - Integer id for the node
# nextblock - If the node is not a split node this will contain a link to the next node in the graph
# trueCase, falseCase - If the node is a split node these will point to the two possible next nodes
class CFGNode:
    def __init__(self, *args):
        self.content = args[0]
        self.text = args[1]
        self.isSplit = args[2]
        self.bbid = args[3]
        self.nextblock = None

    def setNextBlock(self, nextblock):
        self.nextblock = nextblock

    def setBranches(self, trueCase, falseCase):
        self.trueCase = trueCase
        self.falseCase = falseCase


class getVarSet(pointersListener):
    varset = set([])
    def enterVariableName(self, ctx):
        self.varset.add(ctx.getText())


# This class implements a very simple CFG. It could be very fragile but is good enough for our purposes 
class CFG:
    def __init__(self, ast):
        self.startNode = CFGNode(None, 'Start', False, 0)
        finalid, self.cfg, finalNode = CFG.buildCFG(ast.statement(), self.startNode, 0)
        self.endNode = CFGNode(None, 'End', False, finalid+1)
        finalNode.setNextBlock(self.endNode)
        self.maxBBId = finalid+1


    # For each statement we will define here how to add the statement to a CFG
    # The inputs to this function are:
    # 1. the current statment being processed
    # 2. the previous node - so that we can point it to the current node
    # 3. Current highest id for the cfg nodes
    #
    # The function returns the updated bbid, start of the newly added section to the CFG and the end node of the new section.
    def processSingleStatement(statement, prevNode, bbid):
        # For statements that does not impact control flow we create a new object
        # We then set the prevNode's next block as the current  block
        if (isinstance(statement, pointersParser.AssignContext) or
            isinstance(statement, pointersParser.AllocContext) or
            isinstance(statement, pointersParser.SkipContext)):
            newBlock = CFGNode(statement, statement.getText(), False, bbid+1)
            if prevNode:
                prevNode.setNextBlock(newBlock)
            return bbid+1, newBlock, newBlock

        # If the statement is a if condition, 
        if isinstance(statement, pointersParser.IfContext):
            newBlock = CFGNode(None, "IF: [{}]".format(statement.cond.getText()), True, bbid + 1)
            bbid, ifbranch, endNode1 =  CFG.buildCFG(statement.ifs, None, bbid + 1)
            bbid, elsebranch, endNode2 =  CFG.buildCFG(statement.elses, None, bbid)
            newBlock.setBranches(ifbranch, elsebranch)
            if prevNode:
                prevNode.setNextBlock(newBlock)
            joinNode = CFGNode(None, 'Join', False, bbid + 1)            
            endNode1.setNextBlock(joinNode)
            endNode2.setNextBlock(joinNode)
            return bbid + 1, newBlock, joinNode
        
        if isinstance(statement, pointersParser.WhileContext):
            newBlock = CFGNode(statement.cond, "While [{}]".format(statement.cond.getText()), True, bbid+1)
            if prevNode:
                prevNode.setNextBlock(newBlock)            
            bbid, truebranch, endNode1 =  CFG.buildCFG(statement.statement(), None, bbid+1)
            endNode2 =  CFGNode(None, 'skip', False, bbid+1)
            endNode1.setNextBlock(newBlock)            
            newBlock.setBranches(truebranch, endNode2)
            return bbid+1, newBlock, endNode2

        print("[Warning] Not defined statement: ", type(statement))
        return bbid, prevNode, prevNode
        
    # Goes through the AST and builds a CFG
    def buildCFG(program, prevNode, bbid):
        startElement = prevNode
        while len(program) > 0:
            nextStatement = program.pop(0)
            bbid, newNode, endNode = CFG.processSingleStatement(nextStatement, prevNode, bbid)
            if startElement == None:
                startElement = newNode
            prevNode = endNode
        return bbid, startElement, prevNode
       
    def printCFG(start, bbid):
        node = start
        while (node != None):
            if node.isSplit:
                print(node.text, node.bbid)
                CFG.printCFG(node.trueCase, node.bbid)
                CFG.printCFG(node.falseCase, node.bbid)
            else:
                print(node.text, node.bbid)
            if node.nextblock and node.nextblock.bbid <= node.bbid:
                break                
            node = node.nextblock

    def drawCFG(startNode):
        G = nx.DiGraph()
        CFG.drawCFGHelper(startNode, 0, G)        
        nx.nx_agraph.write_dot(G,'test.dot')

    def drawCFGHelper(start, bbid, G):
        nodeFormatStr = "[Id: {}]: {}"
        node = start
        while (node != None):
            G.add_node(nodeFormatStr.format(node.bbid, node.text))
            if node.isSplit:
                CFG.drawCFGHelper(node.trueCase, node.bbid, G)
                CFG.drawCFGHelper(node.falseCase, node.bbid, G)
                G.add_edge(nodeFormatStr.format(node.bbid, node.text),
                           nodeFormatStr.format(node.trueCase.bbid,
                                                node.trueCase.text))
                G.add_edge(nodeFormatStr.format(node.bbid, node.text),
                           nodeFormatStr.format(node.falseCase.bbid,
                                                node.falseCase.text))
            else:
                if node.nextblock: 
                    G.add_edge(nodeFormatStr.format(node.bbid,
                                                    node.text),
                               nodeFormatStr.format(node.nextblock.bbid,
                                                    node.nextblock.text))
            if node.nextblock and node.nextblock.bbid <= node.bbid:
                break
            node = node.nextblock

    def getList(self):
        node = self.startNode
        return CFG.getListHelper(node, [])

    def getListHelper(node, statementList):
        if node.isSplit:
            l1 = CFG.getListHelper(node.trueCase, [])
            l2 = CFG.getListHelper(node.falseCase, [])
            return statementList + [node] + l1 + l2
        else:
            if node.nextblock and node.nextblock.bbid == node.bbid+1:
                return statementList + [node] + CFG.getListHelper(node.nextblock, [])
            else:
                return statementList + [node]
            

class AbstractInterpretation():
    def __init__(self, ast, cfg, absDomain):
        self.ast = ast        
        self.cfg = cfg
        self.absDomain = absDomain
        # The statemap is initialized to have an abstract state for each CFG node. 
        self.stateMap = self.getInitialStateMap()
        # A list of statements are created. The analysis applies the
        # transfer functions along this order.
        self.statementList = cfg.getList()

    
    def getInitialStateMap(self):
        # Following code goes through the code and identifies all the variables used in the program
        variableExplorer = getVarSet()
        walker = ParseTreeWalker()
        walker.walk(variableExplorer, self.ast)

        # Then, for each node in the CFG, following code creates a map
        # from each variable to the bottom element of the abstract domain
        stateMap = {}
        for i in range(self.cfg.maxBBId+1):
            stateMap[i] = dict.fromkeys(variableExplorer.varset, self.absDomain.bottomElement)        
        return stateMap

    def printAbsState(self):
        for key in self.stateMap:
            print(key, repr(sorted(self.stateMap[key].items())))

    def run(self):
        self.runHelper(self.statementList.copy())

    # This function performs the abstract interpretation
    # The input to the function is a list of cfg nodes
    def runHelper(self, nodeList):
        # If the list is empty we are done
        if len(nodeList) == 0:
            return

        # We pop the first node of the list and applies the transformer function on the node
        node = nodeList.pop(0)

        # If the node is not a split node we can apply the transfer function
        # If the transfer function changes the abstract state for the next node we will merge the two states
        if not node.isSplit:
            nextBlock = node.nextblock
            if nextBlock:
                myState = self.stateMap[node.bbid]
                oldState = self.stateMap[nextBlock.bbid].copy()

                # Applying the transfer function based on the abstract domain
                newState = self.absDomain.statementTransfer(nextBlock, myState)
                self.stateMap[nextBlock.bbid] = self.absDomain.merge(oldState, newState)

                if self.absDomain.isEqual(oldState, newState):
                    # If the state did not change we will continue the analysis on the remaining node
                    return self.runHelper(nodeList)
                else:
                    # if the state changed we have not reached a fixed point
                    # In this case we will re add the statement to the list
                    return self.runHelper(nodeList + [nextBlock])
            else:
                # If this is the last node,, do nothing
                return self.runHelper(nodeList)
        else:
            # To handle split nodes we will apply the tranfer function to boith branches
            # We will change the state for the branches if they change due to the transfer function
            myState = self.stateMap[node.bbid]
            oldStateT = self.stateMap[node.trueCase.bbid].copy()            
            newStateT = self.absDomain.statementTransfer(node.trueCase, myState,)
            oldStateF = self.stateMap[node.falseCase.bbid].copy()
            newStateF = self.absDomain.statementTransfer(node.falseCase, myState)

            # If the states chaged we have not reached a fixed point.
            # Based on whether a single path or both paths changed, we
            # will add the statments back to the analysis
            if self.absDomain.isEqual(oldStateT, newStateT):
                if self.absDomain.isEqual(oldStateF, newStateF):
                    return self.runHelper(nodeList)
                else:
                    self.stateMap[node.falseCase.bbid] = self.absDomain.merge(oldStateF, newStateF)
                    return self.runHelper(nodeList + [node.falseCase])
            else:
                self.stateMap[node.trueCase.bbid] = self.absDomain.merge(oldStateT, newStateT)
                if self.absDomain.isEqual(oldStateF, newStateF):
                    return self.runHelper(nodeList + [node.trueCase])
                else:
                    self.stateMap[node.falseCase.bbid] = self.absDomain.merge(oldStateF, newStateF)
                    return self.runHelper(nodeList + [node.trueCase, node.falseCase])


class PointersDomain():
    topElement = set(['null'])
    bottomElement = set([])

    # Returns the least upper bound given two elements (join operator)
    # Implement the latice for Allocation sites here.
    # We have already defined the bottom element to be the empty set and the top element to be a set with ['null']
    # Elements of the abstractDomain are sets of object allocation sites
    def lub(a, b):
        return []

    # Checks if two abstract states are the same
    # Remember that the abstract states map each variable to a element in the abstract domain
    def isEqual(state1, state2):
        return True

    # This is the main transfer function that need to be implemented.
    # For each type of statement define how the currentState get transformed and return the updated state.
    def statementTransfer(block, currentState):
        if isinstance(block.content, pointersParser.SkipContext):
            # what needs to happen if it is a skip statement
            return []
        elif isinstance(block.content, pointersParser.AssignContext):
            # To access the name of the assigned variable you can use block.content.variable(0).getText()
            if not isinstance(block.content.variable(1), pointersParser.NullvarContext):
                # what need to be done if the variable is assigned another variable
                return []
            else:
                # what need to be done if the variable is assigned null                
                return []
        elif isinstance(block.content, pointersParser.AllocContext):
            # how to handle the newObject statement
            # use block.bbid to access the block id of the current CFG node
            # use block.content.variable().getText() to access the variable being assigned
            pass
        else:
            # For split nodes in the CFG we will be adding join nodes. Those nodes do not change the state
            return currentState

    # how do we merge two abstract states together
    # Remember that the abstract states map each variable to a element in the abstract domain
    # hint use the PointersDomain.lub function
    def merge(abstractState1, abstractState2):
        # Replace the return statement. This is currently here to prevent the program crashing. 
        return abstractState1

if __name__ == '__main__':
    input_file = sys.argv[1]

    # Reading the input program and building a CFG
    program_str = open(input_file).read()
    input_stream = InputStream(program_str)
    lexer = pointersLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = pointersParser(stream)
    ast = parser.program()
    cfg = CFG(ast)

    print('--------------')
    CFG.printCFG(cfg.startNode, 0)
    # To generate an image of the CFG use the following command
    # dot -Tpng test.dot -o test.png
    CFG.drawCFG(cfg.startNode)
    print('--------------')

    # Applying Abstract Interpretation
    absInterp = AbstractInterpretation(ast, cfg, PointersDomain)
    absInterp.run()
    absInterp.printAbsState()
    print('--------------')
