from pathlib import Path
from shutil import copytree, rmtree

from phml import PHML, AST, query_all, inspect
from markdown2 import Markdown # https://github.com/trentm/python-markdown2

from padi.nodes import *

phml = PHML()

def _get_components(user_templates: str = ""):
    """Extract user components from the user defined path of custom components"""
    
    path = Path(__file__).parent.joinpath("components")
    phml.add(list(path.glob("**/*.phml")), strip=path.as_posix())

    if user_templates != "":
        path = Path(user_templates).joinpath("components")
        phml.add(list(path.glob("**/*.phml")), strip=path.as_posix())

def _build_file(module: Module, file: File, root: Path, name: str, version: str):
    """Build a specific python files documentation page."""

    return phml.load(root).compile(
        project=name,
        version=version,
        file=file,
        module=module,
        code_highlight=code_highlight
    )
    
def code_highlight(code: str) -> str:
    """Exposed method to templates to allow for python code strings to be highlighted with markdown
    and pygmentize.
    """
    md = Markdown(extras=["fenced-code-blocks"])
    
    return md.convert(f'''\
```python
{code}
```\
''')
    
def _fix_urls(ast: AST, root: str):
    """Any url prefixed with `/` and doesn't start with the website root will
    automatically have the website root prefixed to it. This is applies for all
    elements with `src` or `href` attributes.
    """

    if root != "":
        root = "/" + root.replace('\\', '/').strip('/')
        for link_type in ["href", "src"]:
            for node in query_all(ast, f"[{link_type}^=/]"):
                if not node[link_type].startswith(root):
                    node[link_type] = "/" + root.strip("/") + "/" + node[link_type].lstrip("/")
    return ast
    
def _build_modules(
    root: Module,
    name: str,
    version: str,
    template: Path,
    out: Path,
    *,
    website_root: str = ""
):
    """Build the files and modules inside of a given module."""

    out.joinpath(root["__init__.py"].url.lstrip("/")).mkdir(parents=True, exist_ok=True)
    # Write the home page
    with open(out.joinpath(root["__init__.py"].url.lstrip("/"), "index.html"), "+w", encoding="utf-8") as file:
        phml.ast = _fix_urls(
            _build_file(root, root["__init__.py"], template, name, version),
            website_root
        )
        file.write(phml.render())
    
    for file in root.files():
        if file.file_name != "__init__.py":
            phml.ast = _fix_urls(
                _build_file(root, root[file.file_name], template, name, version),
                website_root
            )
            file_dir = out.joinpath(file.url.lstrip("/"))
            file_dir.mkdir(parents=True, exist_ok=True)
            with open(
                file_dir.joinpath("index.html"), 
                "+w", 
                encoding="utf-8"
            ) as out_file:
                out_file.write(phml.render())
    
    for module in root.sub_modules():
        _build_modules(module, name, version, template, out, website_root=website_root)

def build_docs(
    module: Module,
    project: str,
    version: str = "1",
    *,
    out: str = "docs/",
    root: str = "",
    user_templates: str = ""
) -> str:
    """Build the documentation of the module."""
    
    rmtree(out, ignore_errors=True)
    
    _get_components(user_templates)

    template = Path(__file__).parent.joinpath("module.phml")
    if Path(user_templates).joinpath("module.phml").is_file():
        template = Path(user_templates).joinpath("module.phml")

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        copytree(Path(__file__).parent.joinpath("assets"), Path(out).joinpath("assets"), dirs_exist_ok=True)
    except: pass

    # Write the home page
    # with open(out_dir.joinpath("index.html"), "+w", encoding="utf-8") as file:
    #     file.write(build_module(module, module["__init__.py"], root, project, version))

    # iterate through other files/modules and create their pages
    _build_modules(module, project, version, template, out_dir, website_root=root)
    