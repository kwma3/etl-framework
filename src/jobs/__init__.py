import importlib
import pkgutil
import pathlib

# Dynamically import all job modules in this package to trigger @register_job
pkg_dir = pathlib.Path(__file__).resolve().parent
for _, module_name, _ in pkgutil.iter_modules([str(pkg_dir)]):
    if not module_name.startswith("__"):
        importlib.import_module(f".{module_name}", package=__name__)
