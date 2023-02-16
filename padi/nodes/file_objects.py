from __future__ import annotations
import ast
from markdown2 import Markdown

md = Markdown(extras=["smarty-pants", "strike", "fenced-code-blocks"])

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

class FONode: pass

class Missing(FONode): 
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
    if isinstance(default, ast.Attribute):
        return Attribute(default)
    if isinstance(default, ast.Call):
        return Call(default)
    return default

class DocObject(FONode):
    def __init__(self) -> None:
        self._docstring = ""

    @property
    def type(self) -> str:
        return self.__class__.__name__.lower()

    @property
    def docstring(self) -> str:
        return self._docstring
    
    @property
    def code(self) -> str:
        return "None"
    
    @docstring.setter
    def docstring(self, content: str) -> str:
        content = content.strip().split("\n")
        indents = [len(line) - len(line.lstrip()) for line in content[1:] if line.strip() != ""]
        indent = 0
        for i in indents:
            if i > indent:
                indent = i
        
        for i, line in enumerate(content[1:]):
            offset = max(0, len(line) - len(line.lstrip()) - indent)
            content[i+1] = ' ' * offset + line.lstrip()

        self._docstring = "\n".join(content)

class Annotation(FONode):
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
        elif isinstance(annotation, ast.Attribute):
            self.annotations.append(Attribute(annotation))
        else:
            raise TypeError(f"Unkown annotation type {annotation}")

    class Or(FONode):
        def __init__(self, ops: ast.BinOp) -> None:
            self.left = Annotation(ops.left)
            self.right = Annotation(ops.right)
            
        def __str__(self) -> str:
            return f"{self.left} | {self.right}"
            
    class Subscript(FONode):
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

class Collection(FONode):
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

class Attribute(FONode):
    def __init__(self, attr: ast.Attribute) -> None:
        self.name = get_value(attr.value)
        self.attr = get_value(attr.attr)
    
    def __str__(self) -> str:
        return f"{self.name}.{self.attr}"
    
    def __repr__(self) -> str:
        return f"Attr({self.name}, attr: {self.attr})"

class Assign(DocObject, FONode):
    def __init__(self, attr: ast.Assign) -> None:
        super().__init__()
        self.name = attr.targets[0].id
        self.value = get_value(attr.value) if attr.value is not None else MISSING
        self._docstring = ""
    
    @property
    def code(self) -> str:
        value = self.value
        if isinstance(self.value, str):
            value = repr(self.value)
        
        return f"{self.name} = {value}"
        
    def __repr__(self) -> str:
        return f"Assign({self.name}, value: {self.value})"
        
    def __str__(self) -> str:
        value = (
            f" = {repr(self.value) if isinstance(self.value, str) else self.value}"
            if self.value != MISSING
            else ""
        )
        return f"{self.name}{value}"
    
class AnnAssign(DocObject, FONode):
    def __init__(self, attr: ast.AnnAssign) -> None:
        super().__init__()
        self.name = attr.target.id
        self.annotation = Annotation(attr.annotation) if attr.annotation is not None else MISSING
        self.value = get_value(attr.value) if attr.value is not None else MISSING
        self.simple = bool(attr.simple)
        self._docstring = ""

    @property
    def code(self) -> str:
        value = self.value
        if isinstance(self.value, str):
            value = repr(self.value)
        
        return f"{self.name}: {self.annotation} = {value}"
        
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

class Starred(FONode):
    def __init__(self, starred: ast.Starred) -> None:
        self.name = get_value(starred.value)
    
    def __str__(self) -> str:
        return f"*{self.name}"

class Keyword(FONode):
    def __init__(self, keyword: ast.keyword) -> None:
        self.name = keyword.arg or MISSING
        self.value = get_value(keyword.value)
    
    def __str__(self) -> str:
        if self.name == MISSING:
            return f"**{self.value}"
        else:
            return f"{self.name}={self.name}"

class Call(FONode):
    def __init__(self, _call: ast.Call) -> None:
        self.name = get_value(_call.func)
        self.args = [get_value(arg) for arg in _call.args]
        self.keywords = [Keyword(kw) for kw in _call.keywords]
    
    @property
    def code(self) -> str:
        return str(self)
        
    def __str__(self) -> str:
        args = [*self.args, *self.keywords]      
        return f"{self.name}({', '.join(str(arg) for arg in args)})"

class Class(DocObject, FONode):
    def __init__(self, klass: ast.ClassDef) -> None:
        super().__init__()
        self.attributes = []
        self.methods = []
        self.classes = []
        self.bases = []
        self.name = klass.name
        previous = ""
        
        if (
            len(klass.body) > 0 
            and isinstance(klass.body[0], ast.Expr) 
            and isinstance(klass.body[0].value, ast.Constant)
            and isinstance(klass.body[0].value.value, str)
        ):
            self._docstring = klass.body[0].value.value
        
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
    
    @property
    def code(self) -> str:
        return self.signature()
        
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

class Argument(FONode):
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

class Import(DocObject, FONode):
    def __init__(self, _import: ast.Import | ast.ImportFrom) -> None:
        super().__init__()
        self.module = MISSING
        self.names = []
        self.level = -1 # 0 means absolute import / no `.`
        
        if isinstance(_import, ast.Import):
            self.names = [name.name for name in _import.names]
        elif isinstance(_import, ast.ImportFrom):
            self.module = _import.module or MISSING
            self.names = [name.name for name in _import.names]
            self.level = _import.level
            
    @property
    def is_relative(self) -> bool:
        return self.level > 0

    def __str__(self) -> str:
        if self.level >= 0:
            name = self.module if self.module != MISSING else ''
            return f"from {'.'*self.level + name} import {', '.join(self.names)}"
        return f"import {', '.join(self.names)}"
    
    def __repr__(self) -> str:
        return  f"Import(from: {self.module!r}, names: [{f', '.join(self.names)}, lvl: {self.level}])"

class Method(DocObject, FONode):
    args: list
    """Methods arguments"""
    
    def __init__(self, method: ast.FunctionDef) -> None:
        super().__init__()
        self.name = method.name
        self.decorators = [get_value(decorator) for decorator in method.decorator_list]
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

        if (
            len(method.body) > 0
            and isinstance(method.body[0], ast.Expr)
            and isinstance(method.body[0].value, ast.Constant)
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

    @property
    def code(self) -> str:
        return self.signature()

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

        decorators = [f"@{decorator}" for decorator in self.decorators]
        decorators = "\n".join(decorators) + "\n" if len(decorators) > 0 else ""
        return f"{decorators}def {self.name}({', '.join([arg for arg in args if arg != ''])}){return_anno}"
    
    def __repr__(self) -> str:
        return f"Method({self.name!r})"
    
    def __str__(self) -> str:
        return self.signature()