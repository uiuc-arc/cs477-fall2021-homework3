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

    
    def processSingleStatement(statement, prevNode, bbid):
        if (isinstance(statement, pointersParser.AssignContext) or
            isinstance(statement, pointersParser.AllocContext) or
            isinstance(statement, pointersParser.SkipContext)):
            newBlock = CFGNode(statement, statement.getText(), False, bbid+1)
            if prevNode:
                prevNode.setNextBlock(newBlock)
            return bbid+1, newBlock, newBlock
        
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
                G.add_edge(nodeFormatStr.format(node.bbid, node.text), nodeFormatStr.format(node.trueCase.bbid, node.trueCase.text))
                G.add_edge(nodeFormatStr.format(node.bbid, node.text), nodeFormatStr.format(node.falseCase.bbid, node.falseCase.text))
            else:
                if node.nextblock: 
                    G.add_edge(nodeFormatStr.format(node.bbid, node.text), nodeFormatStr.format(node.nextblock.bbid, node.nextblock.text))
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
        self.stateMap = self.getInitialStateMap()
        self.statementList = cfg.getList()

    def getInitialStateMap(self):
        variableExplorer = getVarSet()
        walker = ParseTreeWalker()
        walker.walk(variableExplorer, self.ast)
        stateMap = {}
        for i in range(self.cfg.maxBBId+1):
            stateMap[i] = dict.fromkeys(variableExplorer.varset, self.absDomain.bottomElement)        
        return stateMap

    def printAbsState(self):
        for key in self.stateMap:
            print(key, self.stateMap[key])

    def run(self):
        self.runHelper(self.statementList.copy())

    def runHelper(self, nodeList):
        if len(nodeList) == 0:
            return 
        node = nodeList.pop(0)
        if not node.isSplit:
            nextBlock = node.nextblock
            if nextBlock:
                myState = self.stateMap[node.bbid]
                oldState = self.stateMap[nextBlock.bbid].copy()
                newState = self.absDomain.statementTransfer(nextBlock, myState, oldState)
                self.stateMap[nextBlock.bbid] = self.absDomain.merge(oldState, newState)
                if self.absDomain.isEqual(oldState, newState):
                    return self.runHelper(nodeList)
                else:
                    return self.runHelper(nodeList + [nextBlock])
            else:
                return self.runHelper(nodeList)
        else:
            myState = self.stateMap[node.bbid]
            oldStateT = self.stateMap[node.trueCase.bbid].copy()            
            newStateT = self.absDomain.statementTransfer(node.trueCase, myState, oldStateT)
            oldStateF = self.stateMap[node.falseCase.bbid].copy()
            newStateF = self.absDomain.statementTransfer(node.falseCase, myState, oldStateF)

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
                

if __name__ == '__main__':
    input_file = sys.argv[1]
    
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

    absInterp = AbstractInterpretation(ast, cfg, PointersDomain)
    absInterp.run()
    absInterp.printAbsState()
    print('--------------')
