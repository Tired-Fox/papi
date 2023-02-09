"""sample_module.parsing.formats

Formating logic for the parsed text that will compile the sample output.
"""
from .decor import decor

class AST:
    """Sample AST."""
    
    def sample(self) -> str:
        """Return a sample of the ast."""
        return ""

@decor
def compile():
    """Compiles a sample ast into a sample output."""
    pass