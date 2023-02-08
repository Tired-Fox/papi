"""sample_module.core 

Handles all high level logic. Like combining parsing and compiling to create
build steps.
"""
from .parsing import decor

__all__ = [
    "build"
]

_protected_var = 1

@decor.decor
def compile_source():
    """Used to create the sample output given [[sample_module.parsing.formats.AST]]
    using [[sample_module.parsing.formats.compile]]."""
    pass

def construct_ast():
    """Used to construct the sample ast with [[sample_module.parsing.formats.AST]]."""
    pass

def build():
    """Main build method for sample_module.
    
    Uses [[sample_module.parsing.parser]] to parse the sample text then
    [[sample_module.parsing.formats]] to compile the parsed tokens into the sample output.
    """
    pass