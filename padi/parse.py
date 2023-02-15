import ast
from pathlib import Path

from .nodes.file_system import Module

ignore_list = ["__main__.py"]
"""List of files to ignore while building the module tree."""

def construct_module(module: str) -> Module:
    """Builds the modules and tree of modules from package/library."""
    root = Module(module, module)
    for file in Path(module).glob("**/*.py"):
        if file.name not in ignore_list:
            root.add(file)
    return root

def docstring(module: Module) -> Module:
    """Gets the docstring for a given module from it's __init__ file."""
    if "__init__.py" in module:
        f_ast = ast.parse(module["__init__.py"].source, module["__init__.py"].full_path)
        return ast.get_docstring(f_ast) or ""