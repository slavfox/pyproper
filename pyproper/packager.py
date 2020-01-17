# Copyright (c) 2020 Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import py_compile
import shutil
from modulefinder import Module, ModuleFinder
from pathlib import Path
from typing import Union


class LibPackager:
    def __init__(self, build_dir: Union[str, Path]):
        if isinstance(build_dir, str):
            self.build_dir = Path(build_dir)
        else:
            self.build_dir = build_dir

        self.zip_build_dir = self.build_dir / "libs" / "lib"
        self.dylib_dir = self.build_dir / "dist" / "lib" / "lib-dynload"

        self.finder = ModuleFinder()

    def find_modules(self, entry_point: str):
        self.finder.run_script(entry_point)
        return self.finder.modules

    def copy_modules(self):
        self.zip_build_dir.mkdir(parents=True, exist_ok=True)
        self.dylib_dir.mkdir(parents=True, exist_ok=True)

        for name, mod in self.finder.modules.items():
            self.copy_module(mod)

        shutil.make_archive(
            self.build_dir / "dist" / "lib" / "pylib",
            "zip",
            str(self.build_dir / "dist"),
        )

    def copy_module(self, module: Module):
        if not module.__file__:
            # sys, builtins, etc - just return quietly
            return
        module_path = Path(module.__file__)
        if module_path.name.endswith(".py"):
            target_path = self.pyc_output_filename(module.__name__)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            py_compile.compile(module_path, target_path)
        else:
            # dynamic libraries, copy them
            shutil.copy(module_path, self.dylib_dir / module_path.name)

    def pyc_output_filename(self, module_name: str):
        segments = module_name.split(".")
        segments[-1] = segments[-1] + ".pyc"
        return self.zip_build_dir.joinpath(*segments)


if __name__ == "__main__":
    p = LibPackager("build")
    p.find_modules("packager.py")
    p.copy_modules()
