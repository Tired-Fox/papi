from pathlib import Path

from phml import PHML

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
        module=file,
        files=module.files()
    )

def build_docs(
    module: Module,
    name: str,
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
    
    with open(out_dir.joinpath("index.html"), "+w", encoding="utf-8") as file:
        file.write(build_module(module, module["__init__.py"], root, name, version))
