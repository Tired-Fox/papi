from pathlib import Path
from shutil import copyfile, copytree

from phml import PHML
from markdown2 import Markdown # https://github.com/trentm/python-markdown2

from padi.nodes import *

phml = PHML()

def get_components(user_templates: str = ""):
    """Extract user components from the user defined path of custom components"""
    
    path = Path(__file__).parent.joinpath("components")
    phml.add(list(path.glob("**/*.phml")), strip=path.as_posix())

    if user_templates != "":
        path = Path(user_templates).joinpath("components")
        phml.add(list(path.glob("**/*.phml")), strip=path.as_posix())

def build_module(module: Module, file: File, root: Path, name: str, version: str):
    return phml.load(root).render(
        project=name,
        version=version,
        file=file,
        module=module,
        code_highlight=code_highlight
    )
    
def code_highlight(code: str) -> str:
    md = Markdown(extras=["fenced-code-blocks"])
    
    return md.convert(f'''\
```python
{code}
```\
''')
    
def build_modules(
    root: Module,
    name: str,
    version: str,
    template: Path,
    out: Path,
):
    
    out.joinpath(root["__init__.py"].url_path).mkdir(parents=True, exist_ok=True)
    # Write the home page
    with open(out.joinpath(root["__init__.py"].url_path, "index.html"), "+w", encoding="utf-8") as file:
        file.write(build_module(root, root["__init__.py"], template, name, version))
    
    for file in root.files():
        if file.file_name != "__init__.py":
            rendered_data = build_module(root, root[file.file_name], template, name, version)
            file_dir = out.joinpath(file.url_path)
            file_dir.mkdir(parents=True, exist_ok=True)
            with open(
                file_dir.joinpath("index.html"), 
                "+w", 
                encoding="utf-8"
            ) as out_file:
                out_file.write(rendered_data)
    
    for module in root.sub_modules():
        build_modules(module, name, version, template, out)

def build_docs(
    module: Module,
    project: str,
    version: str = "1",
    *,
    out: str = "docs/",
    user_templates: str = ""
) -> str:
    """Build the documentation of the module."""
    
    get_components(user_templates)

    root = Path(__file__).parent.joinpath("module.phml")
    if Path(user_templates).joinpath("module.phml").is_file():
        root = Path(user_templates).joinpath("module.phml")

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        copytree(Path(__file__).parent.joinpath("assets"), Path(out).joinpath("assets"), dirs_exist_ok=True)
    except: pass

    # Write the home page
    with open(out_dir.joinpath("index.html"), "+w", encoding="utf-8") as file:
        file.write(build_module(module, module["__init__.py"], root, project, version))

    # iterate through other files/modules and create their pages
    build_modules(module, project, version, root, out_dir)
    