from node_visitor import NodeVisitor
from enum import Enum
from fim_callable import FimClass


class ResolverException(Exception):
    def __init__(self, message=None):
        super().__init__(message)


class FunctionType(Enum):
    NONE = 0
    FUNCTION = 1
    METHOD = 2


class ClassType(Enum):
    NONE = 0
    CLASS = 1


class Resolver(NodeVisitor):
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.scopes = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE
        self.interpreter.set_builtin_globals()
        self.main_was_initialized = False
        self.interfaces_to_be_checked = {}

    def reset(self):
        self.scopes = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE
        self.interpreter.set_builtin_globals()
        self.main_was_initialized = False
        self.interfaces_to_be_checked = {}


    def visit_Compound(self, node):
        self.begin_scope()
        self.resolve_statements(node.children)
        self.end_scope()

    def visit_Trunk(self, node):
        self.resolve_statements(node.children)

    def resolve_statements(self, statements):
        for statement in statements:
            self.visit(statement)

    def resolve(self, node):
        if isinstance(node, list):
            self.resolve_statements(node)
            return
        self.visit(node)

    def begin_scope(self):
        self.scopes.append({})

    def end_scope(self):
        self.scopes.pop()

    def visit_VariableDeclaration(self, node):
        self.declare(node.left)
        if node.right is not None:
            self.visit(node.right)
        self.define(node.left)

    def declare(self, name):
        if len(self.scopes) == 0:
            return
        scope = self.scopes[-1]
        if name.value in scope:
            raise ResolverException(f"{name.value} is already defined")
        scope[name.value] = False

    def define(self, name):
        if len(self.scopes) == 0:
            return
        scope = self.scopes[-1]
        scope[name.value] = True

    def visit_Var(self, node):
        if len(self.scopes) != 0 and self.scopes[-1].get(node.value) is False:
            raise ResolverException()

        self.resolve_local(node, node.token)

    def resolve_local(self, node, name):
        for i in reversed(range(len(self.scopes))):
            if name.value in self.scopes[i]:
                self.interpreter.resolve(node, len(self.scopes) - 1 - i)
                return

    def visit_Assign(self, node):
        self.resolve(node.right)
        self.resolve_local(node.left, node.left.token)

    def visit_Class(self, node):
        self.declare(node.name)
        self.define(node.name)

        self.interpreter.globals.define(node.name.value, node)

        if node.name.value == node.superclass.token.value:
            raise ResolverException(f"A class cannot inherit from itself")

        self.resolve(node.superclass)

        for interface_token in node.implementations:
            if interface_token.value in self.interpreter.globals._values:
                self.check_interface(
                    self.interpreter.globals.get(interface_token.value), node)
            elif interface_token.value in self.interfaces_to_be_checked:
                self.interfaces_to_be_checked[interface_token.value].append(node)
            else:
                self.interfaces_to_be_checked[interface_token.value] = [node]

        self.begin_scope()
        self.scopes[-1]["this"] = True

        for method in node.methods:
            declaration = FunctionType.METHOD
            self.resolve_function(method, declaration)

        self.end_scope()


    def visit_Get(self, node):
        self.resolve(node.object)

    def visit_Set(self, node):
        self.resolve(node.value)
        self.resolve(node.object)

    def visit_Function(self, node):
        self.declare(node.token)
        self.define(node.token)
        self.resolve_function(node, FunctionType.FUNCTION)

    def resolve_function(self, node, function_type):
        if node.is_main:
            if self.main_was_initialized:
                raise ResolverException(f"Cannot have more than one main function")
            self.main_was_initialized = True

        enclosing_function = self.current_function
        self.current_function = function_type

        self.begin_scope()
        for param in node.params:
            self.declare(param)
            self.define(param)
        self.resolve(node.body)
        self.end_scope()
        self.current_function = enclosing_function

    def visit_If(self, node):
        self.resolve(node.condition)
        self.resolve(node.then_branch)
        if node.else_branch is not None:
            self.resolve(node.else_branch)

    def visit_Print(self, node):
        self.resolve(node.expr)

    def visit_Return(self, node):
        if self.current_function == FunctionType.NONE:
            raise ResolverException(f"Cannot return from top-level code")

        if node.value is not None:
            self.resolve(node.value)

    def visit_While(self, node):
        self.resolve(node.condition)
        self.resolve(node.body)

    def visit_DoWhile(self, node):
        self.resolve(node.body)
        self.resolve(node.condition)

    def visit_Increment(self, node):
        self.resolve(node.variable)

    def visit_Decrement(self, node):
        self.resolve(node.variable)

    def visit_String(self, node):
        pass

    def visit_Number(self, node):
        pass

    def visit_BinOp(self, node):
        self.resolve(node.left)
        self.resolve(node.right)

    def visit_FunctionCall(self, node):
        self.resolve(node.name)

        for arg in node.arguments:
            self.resolve(arg)

    def visit_UnaryOp(self, node):
        self.resolve(node.expr)

    def visit_NoOp(self, node):
        pass

    def visit_Bool(self, node):
        pass

    def visit_Null(self, node):
        pass

    def visit_Read(self, node):
        pass

    def visit_Interface(self, node):
        self.interpreter.globals.define(node.name.value, node)
        if node.name.value in self.interfaces_to_be_checked:
            for fim_class in self.interfaces_to_be_checked[node.name.value]:
                self.check_interface(node, fim_class)
        # TODO: сделать интерфейс
        # Как реализовать? В классе, если интерфейса не существует в глобалс,
        # поместить класс в словарь с ключом - названием интерфейса
        # и значением - списком классов-имплементаций.
        # При посещении интерфейса проверять наличие в словаре интерфейсов
        # и проверять методы

    def check_interface(self, interface, fim_class):
        for method in interface.methods:
            if method.name.value not in map(lambda m: m.name.value, fim_class.methods):
                raise ResolverException(f"{fim_class.name.value} does not implement {method.name.value}")

    def visit_Switch(self, node):
        self.resolve(node.variable)
        for case_condition, body in node.cases.items():
            self.resolve(case_condition)
            self.resolve(body)
        if node.default is not None:
            self.resolve(node.default)
