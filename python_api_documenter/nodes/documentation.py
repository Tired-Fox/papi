from __future__ import annotations
import ast
from collections import OrderedDict
from functools import cached_property
from pathlib import Path
from typing import Iterator

from .file_system import Method, Class, Assign, AnnAssign

__all__ = [
    "File",
    "Module"
]

class File:
    def __init__(self, path: str | Path, full_path: str | Path) -> None:
        self.path = path if isinstance(path, Path) else Path(path)
        self.full_path = full_path if isinstance(full_path, Path) else Path(full_path)
        if not self.full_path.is_file():
            raise TypeError(f"{self.path.as_posix()!r} is not a file.")
        
    @cached_property
    def parents(self) -> list[str]:
        return [path for path in self.path.as_posix().split("/")[:-1] if path.strip() != ""]
    
    @cached_property
    def file_name(self) -> str:
        return self.path.name
    
    @cached_property
    def source(self) -> str:
        with open(self.full_path, "r", encoding="utf-8") as file:
            output = file.read()
        return output
    
    @cached_property
    def objects(self) -> list:
        f_ast = ast.parse(self.source, self.full_path)
        objects = []
        previous = ""
        for elem in f_ast.body:
            if isinstance(elem, ast.FunctionDef):
                objects.append(Method(elem).signature())
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
    
    def pretty(self, indent: int = 0) -> str:
        return f"{' '*indent}File({self.file_name!r})"
            
    def __str__(self) -> str:
        return self.pretty()

class Module:
    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self.path = Path(str(path).replace("\\", "/").strip("/"))
        self.nested: OrderedDict[str, Module|File] = OrderedDict()
    
    def __iter__(self):
        nested = OrderedDict(sorted(self.nested.items()))
        for key, value in nested.items():
            yield key, value
            
    def __getitem__(self, key: str):
        return self.nested[key]
    
    def __contains__(self, key: str):
        return key in self.nested
    
    def add(self, obj: str | Path):
        path = str(obj).replace("\\", "/").strip("/").lstrip(self.path.as_posix())
        file = File(path=Path(path), full_path=Path(obj))

        current = self
        for parent in file.parents:
            if parent not in self.nested:
                self.nested[parent] = Module(parent, self.path.joinpath(parent))
            current = self.nested[parent]
        if file.file_name not in current.nested:
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
        out = [f"{' '*indent}Module({self.name!r})"]
        for _, value in self:
            out.append(value.pretty(indent+2))
        return "\n".join(out)
            
    def __str__(self) -> str:
        return self.pretty()