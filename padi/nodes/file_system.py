from __future__ import annotations
import ast
from collections import OrderedDict
from functools import cached_property
from pathlib import Path
from typing import Iterator
from markdown import Markdown

md = Markdown()

from .file_objects import Method, Class, Assign, AnnAssign, Import

__all__ = [
    "File",
    "Module"
]

DocObject = Method | Class | Assign | AnnAssign

class File:
    def __init__(self, path: str | Path, full_path: str | Path) -> None:
        self.path = path if isinstance(path, Path) else Path(path)
        self.full_path = full_path if isinstance(full_path, Path) else Path(full_path)
        self._docstring = ""
        self.parent: Module | None = None
        if not self.full_path.is_file():
            raise TypeError(f"{self.path.as_posix()!r} is not a file.")
        
        f_ast = ast.parse(self.source, self.full_path)
        if (
            len(f_ast.body) > 0
            and isinstance(f_ast.body[0], ast.Expr)
            and isinstance(f_ast.body[0].value, ast.Constant)
            and isinstance(f_ast.body[0].value.value, str)
        ):
            self.docstring = f_ast.body[0].value.value
    
    @property
    def docstring(self) -> str:
        return self._docstring
    
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
    
    @property
    def file_name(self) -> str:
        return self.path.name
    
    @property
    def name(self) -> str:
        if self.file_name == "__init__.py" and self.parent is not  None:
            return self.parent.name
        return self.path.name.replace(self.path.suffix, "")

    @cached_property
    def parents(self) -> list[str]:
        return [path for path in self.path.as_posix().split("/")[:-1] if path.strip() != ""]

    @cached_property
    def url(self) -> list[str]:
        parts = [
                    path 
                    for path in self.full_path.as_posix().split("/")[:-1]
                    if path.strip() != ""
                ][1:]
        if self.parent is not None and self.name != self.parent.name:
            parts.append(self.name)
        return '/' + '/'.join(parts) + '/'
    
    @cached_property
    def source(self) -> str:
        with open(self.full_path, "r", encoding="utf-8") as file:
            output = file.read()
        return output

    @cached_property
    def objects(self) -> list[DocObject]:
        f_ast = ast.parse(self.source, self.full_path)
        objects = []
        previous = ""
        for elem in f_ast.body:
            if isinstance(elem, ast.FunctionDef):
                objects.append(Method(elem))
                previous = "method"
            elif isinstance(elem, ast.ClassDef):
                objects.append(Class(elem))
                previous = "class"
            elif isinstance(elem, ast.Assign):
                objects.append(Assign(elem))
                previous = "assign"
            elif isinstance(elem, ast.AnnAssign):
                objects.append(AnnAssign(elem))
                previous = "assign"
            elif isinstance(elem, ast.Expr) and previous == "assign" and isinstance(elem.value.value, str):
                objects[-1].docstring = elem.value.value
                previous = "expr"
            else:
                # Unhandled ast node
                previous = ""
        return objects
    
    @cached_property
    def protected(self) -> list[DocObject]:
        return [object for object in self.objects if object.name.startswith("_") and not object.name.startswith("__")]
    
    @cached_property
    def private(self) -> list:
        return [object for object in self.objects if object.name.startswith("__")]
    
    @cached_property
    def public(self) -> list:
        return [object for object in self.objects if not object.name.startswith("_")]
    
    @cached_property
    def methods(self) -> list:
        return [object for object in self.objects if isinstance(object, Method)]
    
    @cached_property
    def classes(self) -> list:
        return [object for object in self.objects if isinstance(object, Class)]
    
    @cached_property
    def Assignments(self) -> list:
        return [object for object in self.objects if isinstance(object, (Assign, AnnAssign))]
    
    @cached_property
    def imports(self) -> list:
        return [
            Import.create(node)
            for node in ast.parse(self.source, self.full_path).body 
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
    
    def pretty(self, indent: int = 0) -> str:
        return f"{' '*indent}File({self.file_name!r})"
            
    def __str__(self) -> str:
        return self.pretty()

class Module:
    def __init__(self, name: str, path: str, parent: Module | None = None) -> None:
        self.name = name
        self.path = Path(str(path).replace("\\", "/").strip("/"))
        self.parent = parent
        self.nested: OrderedDict[str, Module|File] = OrderedDict()
    
    def __iter__(self):
        nested = OrderedDict(sorted(self.nested.items()))
        for key, value in nested.items():
            yield key, value
            
    def __getitem__(self, key: str):
        return self.nested[key]
    
    def __contains__(self, key: str):
        return key in self.nested
    
    @cached_property
    def url(self) -> list[str]:
        if '__init__.py' in self:
            return self['__init__.py'].url
        else:
            return "/"
    
    def add(self, obj: str | Path):
        path = str(obj).replace("\\", "/").strip("/").lstrip(self.path.as_posix())
        file = File(path=Path(path), full_path=Path(obj))

        current = self
        for parent in file.parents:
            if parent not in current:
                current.nested[parent] = Module(parent, self.path.joinpath(parent), current)
            current = current[parent]
        if file.file_name not in current.nested:
            file.parent = current
            current.nested[file.file_name] = file

    def files(self) -> Iterator[File]:
        for _, value in self:
            if isinstance(value, File):
                yield value
    
    def sub_modules(self) -> Iterator[Module]:
        for _, value in self:
            if isinstance(value, Module):
                yield value
            
    def pretty(self, indent: int = 0) -> str:
        out = [f"{' '*indent}Module({self.name!r}, {self.parent.name if self.parent is not None else ''!r})"]
        for _, value in self:
            out.append(value.pretty(indent+2))
        return "\n".join(out)
            
    def __str__(self) -> str:
        return self.pretty()
    