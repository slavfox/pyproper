# Copyright (c) 2020, Slavfox
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from distutils.ccompiler import new_compiler, CCompiler
from distutils.sysconfig import (
    customize_compiler,
    get_python_inc,
    get_python_lib
)
from pathlib import Path
import platform
from typing import Union

import cffi

pyproper_dir = Path(__file__).resolve().parent

C_ENTRY_POINT_SRC = r'''
#ifndef CFFI_DLLEXPORT
#  if defined(_MSC_VER)
#    define CFFI_DLLEXPORT  extern __declspec(dllimport)
#  else
#    define CFFI_DLLEXPORT  extern
#  endif
#endif

CFFI_DLLEXPORT int py_main(int argc, char *argv[]);
'''

C_EXECUTABLE_SRC = r'''
int py_main(int argc, char *argv[]);
int main(int argc, char *argv[]){
    return py_main(argc, argv);
};
'''


class Compiler:
    def __init__(
        self,
        libname: str,
        entry_point: str,
        build_dir: Path,
        compiler: str = None,
        libpython_dir: Union[str, Path] = None
    ):
        self.libname: str = libname
        self.entry_point: str = entry_point
        self.build_dir: Path = build_dir
        self._entry_point_source_path: Path = build_dir / 'entry_point.c'
        self._executable_filename = f'{libname}_{entry_point}.c'
        self._builder = None

        if isinstance(libpython_dir, str):
            self.libpython_dir = Path(libpython_dir)
        else:
            self.libpython_dir = libpython_dir

        self._compiler: CCompiler = new_compiler(compiler)
        customize_compiler(self._compiler)

    @property
    def ffi_builder(self) -> cffi.FFI:
        if self._builder is None:
            self._make_builder()
        return self._builder

    def _make_builder(self):
        ffi_builder = cffi.FFI()
        ffi_builder.embedding_api('int py_main(int argc, char *argv[]);')

        ffi_builder.set_source(
            "entry_point",
            C_ENTRY_POINT_SRC,
            include_dirs=[str(pyproper_dir)]
        )

        ffi_builder.embedding_init_code(f"""
            from entry_point import ffi
            from {self.libname} import {self.entry_point}
        
            @ffi.def_extern()
            def py_main(argc, argv):
                return {self.entry_point}(argv)
        """)
        self._builder = ffi_builder

    def output_sources(self):
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.ffi_builder.emit_c_code(
            str(self._entry_point_source_path.resolve())
        )
        with (self.build_dir / self._executable_filename).open('w') as f:
            f.write(C_EXECUTABLE_SRC)

    def init_compiler(self):
        self._compiler.add_include_dir(get_python_inc())
        self._compiler.add_library_dir(get_python_lib())
        if platform.python_implementation() == 'PyPy':
            # ToDo: this needs to be shipped
            self._compiler.add_library("pypy-c")

    def compile(self):
        self.output_sources()
        self.init_compiler()
        objs = self._compiler.compile([
            str(self._entry_point_source_path),
            str(self.build_dir / self._executable_filename)
        ])
        print("donezo")
        print(self._compiler.link_executable(objs, self.libname))


if __name__ == '__main__':
    c = Compiler(
        'pathlib', 'Path',
        Path('build'),
        libpython_dir='/Users/fox/.pyenv/versions/pypy3.6-7.1.1/lib'
    )
    c.compile()
