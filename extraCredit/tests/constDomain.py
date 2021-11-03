class ConstDomain(AbstractDomain):
    topElement = "Top"
    bottomElement = "Bot"

    # Returns the least upper bound given two elements
    def lub(a, b):
        if a==ConstDomain.bottomElement:
            return b
        elif b==ConstDomain.bottomElement:
            return a
        elif a==b:
            return a
        else:
            return ConstDomain.topElement

    def isConst(val):
        if val != ConstDomain.topElement and val != ConstDomain.bottomElement:
            return True
        else:
            return False

    def isEqual(state1, state2):
        for key in state1.keys():
            if state1[key] != state2[key]:
                return False
        return True

    def handleBinaryExpression(expression, abstractState, opr):
        lhs = ConstDomain.absEvalExpression(expression.expression(0), abstractState)
        rhs = ConstDomain.absEvalExpression(expression.expression(1), abstractState)
        # Check if both sides of the expression is a constant
        if ConstDomain.isConst(lhs) and ConstDomain.isConst(rhs):
            return opr(lhs, rhs)
        if lhs == ConstDomain.bottomElement and rhs == ConstDomain.bottomElement:
            return ConstDomain.bottomElement
        else:
            return ConstDomain.topElement
        return (lhs, rhs)

    def absEvalExpression(expression, abstractState):
        if isinstance(expression, pointersParser.LiteralContext):
            return int(expression.getText())
        if isinstance(expression, pointersParser.VariableExprContext):
            return abstractState[expression.getText()]
        if isinstance(expression, pointersParser.ParanContext):
            return ConstDomain.absEvalExpression(expression.expression(), abstractState)
        if isinstance(expression, pointersParser.MultiplyContext):
            return ConstDomain.handleBinaryExpression(expression, abstractState, operator.mul)
        if isinstance(expression, pointersParser.DivideContext):
            return ConstDomain.handleBinaryExpression(expression, abstractState, operator.div) 
        if isinstance(expression, pointersParser.AddContext):
            return ConstDomain.handleBinaryExpression(expression, abstractState, operator.add)
        if isinstance(expression, pointersParser.MinusContext):
            return ConstDomain.handleBinaryExpression(expression, abstractState, operator.sub)

    def statementTransfer(block, currentState, nextAbstractState):
        if isinstance(block.content, pointersParser.SkipContext):
            return currentState
        elif isinstance(block.content, pointersParser.AssignContext):
            newAbstractState = currentState.copy()
            value = ConstDomain.absEvalExpression(block.content.expression(), currentState)
            newAbstractState[block.content.variable().getText()] = value
            return newAbstractState
        elif isinstance(block.content, pointersParser.PointerAssignContext):            
            return currentState
        elif isinstance(block.content, pointersParser.MallocContext):
            newAbstractState = currentState.copy()
            newAbstractState[block.content.variable()] = ConstDomain.topElement
            return newAbstractState
        else:
            return currentState

    def merge(abstractState1, abstractState2):
        newAbstractState = {}
        for key in abstractState1.keys():
            newAbstractState[key] = ConstDomain.lub(abstractState1[key], abstractState2[key])
        return newAbstractState
