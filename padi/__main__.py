import click

from . import __version__
from .parse import construct_module
from .compile.documentation import build_docs

@click.group(invoke_without_command=True)
def cli(version: bool):
    """Customaizable and easy to use python api Documenter"""

    if version:
        print(f"pyAPI v{__version__}")

@click.argument("module", default="")
@click.option("-v", "--version", flag_value=True, help="Version of the Documenter", default=False)
@click.option("-o", "--output", help="Output directory of the files.", default="docs/")
@click.option(
    "-l", 
    "--layouts", 
    help="Directory where the layout phml files are located", 
    default=""
)
@click.command()
def documentation(module: str,  output: str, layouts: str, version: bool) -> dict:
    if version:
        print(f"pyAPI v{__version__}")
        exit()

    root = construct_module(module)
    
    build_docs(root, module, user_templates=layouts)

if __name__ == "__main__":
    documentation()