import fim_ast
from fim_lexer import Literals
from fim_lexer import Keywords
from fim_lexer import Suffix
from fim_lexer import Block


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def error(self):
        raise Exception('Invalid syntax')

    def eat(self, token_name, token_block=None, token_suffix=None):
        if self.current_token.name == token_name\
                and ((token_block is None) or (token_block == self.current_token.block))\
                and ((token_suffix is None) or (token_suffix == self.current_token.suffix)):
            self.current_token = self.lexer.get_next_token()
        else:
            self.error()

    def class_statement(self):
        self.eat(Keywords.REPORT, token_block=Block.BEGIN)
        superclass_token = self.current_token
        self.eat('NAME')

        implementations = []
        while self.current_token.name == Keywords.AND:
            self.eat(Keywords.AND)
            implementations.append(self.current_token)
            self.eat('NAME')
        self.eat(Keywords.PUNCTUATION)

        class_token = self.current_token
        self.eat('NAME')

        self.eat(Keywords.PUNCTUATION)
        body = self.statement_list()

        self.eat(Keywords.REPORT, token_block=Block.END)
        self.eat(Keywords.PUNCTUATION)
        programmer_token = self.current_token
        self.eat('NAME')

        return fim_ast.Class(
            class_token, superclass_token, implementations, body, programmer_token)

    def method_statement(self):
        self.eat(Keywords.PARAGRAPH, token_block=Block.BEGIN)
        name = self.current_token
        self.eat('NAME')

        return_type = None
        if self.current_token.name == Keywords.RETURNED_VARIABLE_TYPE:
            self.eat(Keywords.RETURNED_VARIABLE_TYPE)
            return_type = self.current_token
            self.eat('NAME')

        parameters = []
        if self.current_token.name == Keywords.LISTING_PARAGRAPH_PARAMETERS:
            self.eat(Keywords.LISTING_PARAGRAPH_PARAMETERS)
            while self.current_token.name == Keywords.AND:
                self.eat(Keywords.AND)
                parameters.append(self.current_token)
                self.eat('NAME')
        self.eat(Keywords.PUNCTUATION)

        body = self.statement_list()

        self.eat(Keywords.PARAGRAPH, token_block=Block.END)
        name_in_ending = self.current_token
        if name.value != name_in_ending.value:
            self.error()
        self.eat('NAME')

        return fim_ast.Method(name, return_type, parameters, body)

    def return_statement(self):
        self.eat(Keywords.RETURN)
        node = fim_ast.Return(self.expr())
        return node

    def run_statement(self):
        self.eat(Keywords.RUN)
        node = self.expr()
        return node

    def method_call_expr(self):
        token = self.current_token
        self.eat('NAME')

        parameters = []
        if self.current_token.name == Keywords.LISTING_PARAGRAPH_PARAMETERS:
            self.eat(Keywords.LISTING_PARAGRAPH_PARAMETERS)
            while self.current_token.name == Keywords.AND:
                self.eat(Keywords.AND)
                parameters.append(self.current_token.value)
                self.eat('NAME')
            self.eat('NAME')

        node = fim_ast.MethodCall(token, parameters)
        return node

    def compound_statement(self):
        # compound_name = self.current_token.name
        # self.eat(compound_name, token_block=Block.BEGIN)
        nodes = self.statement_list()
        # self.eat(compound_name, token_block=Block.END)

        root = fim_ast.Compound()
        for node in nodes:
            root.children.append(node)

        return root

    def statement_list(self):
        node = self.statement()

        results = [node]

        while self.current_token.name == Keywords.PUNCTUATION:
            self.eat(Keywords.PUNCTUATION)
            results.append(self.statement())

        if self.current_token.name == 'NAME':
            self.error()

        return results

    def statement(self):
        #if self.current_token.block == Block.BEGIN:
        #    node = self.compound_statement()
        #el
        if self.current_token.name == Keywords.VAR:
            node = self.assignment_statement()
        elif self.current_token.name == Keywords.PRINT:
            node = self.print_statement()
        else:
            node = self.empty()
        return node

    def assignment_statement(self):
        self.eat(Keywords.VAR, token_suffix=Suffix.PREFIX)
        left = self.variable()
        token = self.current_token
        self.eat(Keywords.VAR, token_suffix=Suffix.INFIX)
        right = self.expr()
        node = fim_ast.Assign(left, token, right)
        return node

    def print_statement(self):
        self.eat(Keywords.PRINT)
        node = fim_ast.Print(self.expr())
        return node

    def read_statement(self):
        self.eat(Keywords.READ)
        node = fim_ast.Read(self.variable())
        return node

    def prompt_statement(self):
        read_node = self.read_statement()
        node = fim_ast.Prompt(read_node, self.expr())
        return node

    def variable(self):
        node = fim_ast.Var(self.current_token)
        self.eat('NAME')
        return node

    @staticmethod
    def empty():
        """An empty production"""
        return fim_ast.NoOp()

    def factor(self):
        token = self.current_token
        if token.name == Literals.NUMBER:
            self.eat(Literals.NUMBER)
            return fim_ast.Number(token)
        elif token.name == Literals.STRING:
            self.eat(Literals.STRING)
            return fim_ast.String(token)
        elif token.name == Literals.CHAR:
            self.eat(Literals.CHAR)
            return fim_ast.Char(token)
        elif token.name == Literals.TRUE:
            self.eat(Literals.TRUE)
            return fim_ast.Bool(token)
        elif token.name == Literals.FALSE:
            self.eat(Literals.FALSE)
            return fim_ast.Bool(token)
        elif token.name == Literals.NULL:
            self.eat(Literals.NULL)
            return fim_ast.Null(token)
        else:
            node = self.variable()
            return node

    def term(self):
        if self.current_token.name in (Keywords.MULTIPLICATION, Keywords.DIVISION)\
                and self.current_token.suffix == Suffix.PREFIX:
            token = self.current_token
            self.eat(token.name, token_suffix=Suffix.PREFIX, token_block=Block.BEGIN_PARTNER)
            left = self.term()
            self.eat(token.name, token_suffix=Suffix.INFIX, token_block=Block.END_PARTNER)
            right = self.term()
            node = fim_ast.BinOp(op=token, left=left, right=right)
            return node
        else:
            node = self.factor()
            while self.current_token.name in (Keywords.MULTIPLICATION, Keywords.DIVISION)\
                    and self.current_token.suffix == Suffix.INFIX and self.current_token.block == Block.NONE:
                token = self.current_token
                if token.name == Keywords.MULTIPLICATION:
                    self.eat(Keywords.MULTIPLICATION)
                elif token.name == Keywords.DIVISION:
                    self.eat(Keywords.DIVISION)
                node = fim_ast.BinOp(left=node, op=token, right=self.factor())
            return node

    def expr(self):
        if self.current_token.name in (Keywords.ADDITION, Keywords.SUBTRACTION)\
                and self.current_token.suffix == Suffix.PREFIX:
            token = self.current_token
            self.eat(token.name, token_suffix=Suffix.PREFIX)
            left = self.term()
            self.eat(token.name, token_suffix=Suffix.INFIX)
            right = self.term()
            node = fim_ast.BinOp(op=token, left=left, right=right)
            return node
        else:
            node = self.term()
            while self.current_token.name in (Keywords.ADDITION, Keywords.SUBTRACTION, Keywords.AND)\
                    and self.current_token.suffix == Suffix.INFIX and self.current_token.block == Block.NONE:
                token = self.current_token
                if token.name == Keywords.ADDITION:
                    self.eat(Keywords.ADDITION, token_suffix=Suffix.INFIX)
                elif token.name == Keywords.AND:
                    self.eat(Keywords.ADDITION, token_suffix=Suffix.INFIX)
                elif token.name == Keywords.SUBTRACTION:
                    self.eat(Keywords.SUBTRACTION, token_suffix=Suffix.INFIX)
                node = fim_ast.BinOp(left=node, op=token, right=self.term())
            return node

    def parse(self):
        return self.compound_statement()
