from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "kinematic_wave_parallel_tools",
        ["kinematic_wave_parallel_tools.pyx"],
        extra_compile_args=["-O3", "-ffast-math", "-march=native", "-fopenmp"],
        extra_link_args=["-fopenmp"]
    )
]

setup(
    name='kinematic_wave-parallel',
    ext_modules=cythonize(ext_modules, annotate=True),
)
