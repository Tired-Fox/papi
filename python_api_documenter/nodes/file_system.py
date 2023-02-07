from __future__ import annotations
import ast

__all__ = [
    "MISSING",
    "get_value",
    "Annotation",
    "Collection",
    "Assign",
    "AnnAssign",
    "Class",
    "Method",
    "Argument"
]

class Missing: 
    def __repr__(self) -> str:
        return f"MISSING"

MISSING = Missing()

def get_value(default):
    if isinstance(default, ast.Constant):
        return default.value
    if isinstance(default, ast.Name):
        return Annotation(default)
    if isinstance(default, (ast.List, ast.Tuple, ast.Set)):
        return Collection(default)
    raise TypeError(f"Unkown default value: {default}")

class Annotation:
    def __init__(self, annotation) -> None:
        self.annotations = []
        if isinstance(annotation, ast.Name):
            self.annotations.append(annotation.id)
        elif isinstance(annotation, ast.Subscript):
            self.annotations.append(Annotation.Subscript(annotation))
        elif isinstance(annotation, ast.BinOp):
            self.annotations.append(Annotation.Or(annotation))
        elif isinstance(annotation, ast.Constant) and annotation.value is None:
            self.annotations.append("None")
        else:
            raise TypeError(f"Unkown annotation type {annotation}")

    class Or:
        def __init__(self, ops: ast.BinOp) -> None:
            self.left = Annotation(ops.left)
            self.right = Annotation(ops.right)
            
        def __str__(self) -> str:
            return f"{self.left} | {self.right}"
            
    class Subscript:
        def __init__(self, subscript: ast.Subscript) -> None:
            self.name = subscript.value.id
            self.annotations = []
            if isinstance(subscript.slice, ast.Tuple):
                for element in subscript.slice.elts:
                    self.annotations.append(Annotation(element))
        
        def __str__(self) -> str:
            return f"{self.name}[{', '.join(str(annotation) for annotation in self.annotations)}]"
            
    def __str__(self) -> str:
        return ", ".join(str(annotation) for annotation in self.annotations)

class Collection:
    def __init__(self, collection: ast.List | ast.Tuple | ast.Set) -> None:
        self.brackets = ["(", ")"] if isinstance(collection, (ast.Tuple, ast.Set)) else ["[", "]"]
        self.elements = [get_value(element) for element in collection.elts]
        self.trailing = "," if isinstance(collection, ast.Set) else ""

    def __str__(self) -> str:
        elements = []
        for element in self.elements:
            if isinstance(element, str):
                elements.append(repr(element))
            else:
                elements.append(element)

        return f"{self.brackets[0]}\
{', '.join(elements)}\
{self.brackets[1]}{self.trailing}"

class Assign:
    def __init__(self, attr: ast.Assign) -> None:
        self.name = attr.targets[0].id
        self.value = get_value(attr.value) if attr.value is not None else MISSING
        self.docstring = ""
        
    def __repr__(self) -> str:
        return f"Assign({self.name}, value: {self.value})"
        
    def __str__(self) -> str:
        value = (
            f" = {repr(self.value) if isinstance(self.value, str) else self.value}"
            if self.value != MISSING
            else ""
        )
        return f"{self.name}{value}"
    
class AnnAssign:
    def __init__(self, attr: ast.AnnAssign) -> None:
        self.name = attr.target.id
        self.annotation = Annotation(attr.annotation) if attr.annotation is not None else MISSING
        self.value = get_value(attr.value) if attr.value is not None else MISSING
        self.simple = bool(attr.simple)
        self.docstring = ""
        
    def __repr__(self) -> str:
        return f"Attr({self.name}, anno: {self.annotation}, value: {self.value})"
        
    def __str__(self) -> str:
        annotation = f": {self.annotation}" if self.annotation != MISSING else ""
        value = (
            f" = {repr(self.value) if isinstance(self.value, str) else self.value}"
            if self.value != MISSING
            else ""
        )
        return f"{self.name}{annotation}{value}"

class Class:
    def __init__(self, klass: ast.ClassDef) -> None:
        self.attributes = []
        self.methods = []
        self.classes = []
        self.bases = []
        self.name = klass.name
        previous = ""
        for node in klass.body:
            if isinstance(node, ast.AnnAssign):
                self.attributes.append(AnnAssign(node))
                previous = "attribute"
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, str) and previous == "attribute":
                    self.attributes[-1].docstring = node.value
                previous = "expr"
            elif isinstance(node, ast.FunctionDef):
                self.methods.append(Method(node))
            elif isinstance(node, ast.ClassDef):
                self.classes.append(Class(node))
        
        for base in klass.bases:
            self.bases.append(base.id)
        
    def signature(self) -> str:
        inherits = f"({', '.join(self.bases)})" if len(self.bases) > 0 else ""
        return f"class {self.name}{inherits}"

    def __str__(self) -> str:
        out = [self.signature()]
        for method in self.methods:
            out.append('   ' + method.signature())
        
        for klass in self.classes:
            out.append('   ' + klass.signature())
        return "\n".join(out)

class Argument:
    def __init__(self, arg: ast.arg) -> None:
        self.name = arg.arg
        self.annotation = Annotation(arg.annotation) if arg.annotation is not None else MISSING
        self.default = MISSING
    
    def __str__(self) -> str:
        annot = f": {self.annotation}" if self.annotation != MISSING else ""
        default = (
            f" = {repr(self.default) if isinstance(self.default, str) else self.default}" 
            if self.default != MISSING 
            else ""
        )
        return f"{self.name}{annot}{default}"
    
    def __repr__(self) -> str:
        return f"Arg({self.name!r}, {self.annotation!r}, {self.default!r})"

class Method:
    args: list
    """Methods arguments"""
    
    def __init__(self, method: ast.FunctionDef) -> None:
        self.name = method.name

        (
            self.posonlyargs,
            self.args,
            defaults,
            self.kwonlyargs,
            kw_defaults,
            self.vararg,
            self.kwarg,
        ) = self.parse_args(method)
        
        default_index = len(defaults)
        for arg, default in zip(reversed(self.args), defaults):
            arg.default = default
            default_index -= 1
        
        if default_index > 0:
            for arg, default in zip(reversed(self.posonlyargs), defaults):
                arg.default = default
                default_index -= 1
                
        for arg, default in zip(reversed(self.kwonlyargs), kw_defaults):
            arg.default = default

        self.docstring = ""
        if (
            len(method.body) > 0
            and isinstance(method.body[0], ast.Expr)
            and isinstance(method.body[0].value.value, str)
        ):
            self.docstring = method.body[0].value.value
            
        self.returns = MISSING
        if method.returns is not None:
            self.returns = Annotation(method.returns)
            
    def parse_args(self, method: ast.FunctionDef) -> tuple[list, list, list, list, str, str]:
        args = method.args
        
        return (
            [Argument(arg) for arg in args.posonlyargs],                    # posonlyargs
            [Argument(arg) for arg in args.args],                           # args
            [get_value(arg) for arg in args.defaults],                    # defaults
            [Argument(arg) for arg in args.kwonlyargs],                     # kwonlyargs
            [get_value(arg) for arg in args.kw_defaults],                 # kw_defaults
            Argument(args.vararg) if args.vararg is not None else MISSING,  # vararg
            Argument(args.kwarg) if args.kwarg is not None else MISSING,    # kwarg
        )
        
    def signature(self) -> str:
        return_anno = f" -> {self.returns}" if self.returns != MISSING else ""

        args = [
            ', '.join([str(arg) for arg in self.posonlyargs]),
            "/" if len(self.posonlyargs) > 0 else "",
            ', '.join([str(arg) for arg in self.args]),
            '*' if len(self.kwonlyargs) > 0 else "",
            ', '.join([str(arg) for arg in self.kwonlyargs]),
            f"*{self.vararg}" if self.vararg != MISSING else "",
            f"**{self.kwarg}" if self.kwarg != MISSING else ""
        ]

        return f"def {self.name}({', '.join([arg for arg in args if arg != ''])}){return_anno}"
    
    def __str__(self) -> str:
        return self.signature()