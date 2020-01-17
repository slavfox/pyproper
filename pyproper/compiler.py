# Copyright (c) 2020, Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Pyproper compiler entry point.

This module holds the Compiler class, which handles building the actual
executable.
"""
import platform
import sys
from distutils.ccompiler import CCompiler, new_compiler
from distutils.sysconfig import (
    customize_compiler,
    get_python_inc,
    get_python_lib,
)
from os import path
from pathlib import Path
from typing import Union

import cffi

pyproper_dir = Path(__file__).resolve().parent


class Compiler:

    PY_MAIN_DECL = "int py_main(int argc, char *argv[]);"

    PY_INIT_SRC = """
    from entry_point import ffi

    @ffi.def_extern()
    def py_main(argc, argv):
        import sys
        sys.argv[:] = [ffi.string(argv[i]).decode() for i in range(argc)]
        print(__file__)
        return 1
    """

    C_ENTRY_POINT_SRC = f"""
    #ifndef CFFI_DLLEXPORT
    #  if defined(_MSC_VER)
    #    define CFFI_DLLEXPORT  extern __declspec(dllimport)
    #  else
    #    define CFFI_DLLEXPORT  extern
    #  endif
    #endif

    CFFI_DLLEXPORT {PY_MAIN_DECL}
    """

    C_EXECUTABLE_SRC = f"""
    #include <Python.h>

    {PY_MAIN_DECL}
    
    int main(int argc, char *argv[]){{
        return py_main(argc, argv);
    }};
    """

    def __init__(
        self,
        program_name: str,
        build_dir: Union[str, Path],
        compiler: str = None,
        libpython_dir: Union[str, Path] = None,
    ):
        self.program_name: str = program_name

        if isinstance(libpython_dir, str):
            self.libpython_dir = Path(libpython_dir)
        else:
            self.libpython_dir = libpython_dir

        if isinstance(build_dir, str):
            self.build_dir = Path(build_dir)
        else:
            self.build_dir = build_dir

        self._src_path: Path = self.build_dir / "src"
        self._entry_point_c_path: Path = self._src_path / "entry_point.c"
        self._executable_filename = f"{program_name}.c"

        self.ffi_builder: cffi.FFI = self._make_ffi_builder()
        self._compiler: CCompiler = new_compiler(compiler)
        customize_compiler(self._compiler)

    def _make_ffi_builder(self):
        ffi_builder = cffi.FFI()
        ffi_builder.embedding_api(self.PY_MAIN_DECL)

        ffi_builder.set_source(
            "entry_point",
            self.C_ENTRY_POINT_SRC,
            include_dirs=[str(pyproper_dir)],
        )

        ffi_builder.embedding_init_code(self.PY_INIT_SRC.format())
        return ffi_builder

    def _prepare_entry_point(self):
        pass

    def output_sources(self):
        self._src_path.mkdir(parents=True, exist_ok=True)
        self.ffi_builder.emit_c_code(str(self._entry_point_c_path))
        with (self._src_path / self._executable_filename).open("w") as f:
            f.write(self.C_EXECUTABLE_SRC)

    def init_compiler(self):
        py_inc = get_python_inc()
        platspec_py_inc = get_python_inc(plat_specific=1)

        self._compiler.add_include_dir(py_inc)
        self._compiler.add_include_dir(platspec_py_inc)
        self._compiler.add_library_dir(get_python_lib())

        # Workaround for virtualenvs
        if sys.exec_prefix != sys.base_exec_prefix:
            self._compiler.add_include_dir(
                path.join(sys.exec_prefix, "include")
            )
            self._compiler.add_library_dir(path.join(sys.exec_prefix, "lib"))

        if platform.python_implementation() == "PyPy":
            # ToDo: this needs to be shipped
            self._compiler.add_library("pypy-c")
        else:
            self._compiler.add_library("python3.8")

    def compile(self, debug=False):
        self.output_sources()
        self.init_compiler()
        objs = self._compiler.compile(
            [
                str(self._entry_point_c_path),
                str(self._src_path / self._executable_filename),
            ],
            debug=debug,
        )
        self._compiler.link_executable(
            objs, self.program_name, str(self.build_dir / "dist")
        )


if __name__ == "__main__":
    c = Compiler(
        "pathlib",
        Path("build"),
        libpython_dir="/Users/fox/.pyenv/versions/pypy3.6-7.1.1/lib",
    )
    c.compile(True)
