# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

from distutils.command.build_scripts import build_scripts
from itertools import chain
from os import chmod, getcwd, listdir, walk as walk_path
from os.path import join as path_join, splitext as split_ext
from pprint import pprint
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
from sys import stderr


package_roots = ['craft', 'iotest', 'pithy']
modules = ['utest']
bin_src_dirs = ['craft/bin', 'iotest/bin', 'pithy/bin']

def errSL(*items): print(*items, file=stderr)


class BuildScripts(build_scripts):
  def run(self):
    super().run()
    #errSL("\nBUILD SCRIPTS")
    #pprint(vars(self))

class Develop(develop):
  def run(self):
    super().run()
    errSL("\nDEVELOP")
    #pprint(vars(self))
    gen_bins(bin_dst_dir=self.script_dir)

class Install(install):
  def run(self):
    super().run()
    errSL(f"\nINSTALL")
    #pprint(vars(self))
    #errSL('\ndistribution:')
    #pprint(vars(self.distribution))
    #errSL('\ncommand_obj:')
    #pprint(self.distribution.command_obj)
    gen_bins(bin_dst_dir=self.install_scripts)

def gen_bins(*, bin_dst_dir:str) -> None:
  errSL('bin_dst_dir:', bin_dst_dir)
  assert bin_dst_dir.startswith('/'), bin_dst_dir
  py_path = path_join(bin_dst_dir, 'python3')
  for src_dir in bin_src_dirs:
    for name in listdir(src_dir):
      stem, ext = split_ext(name)
      if stem[0] in '._' or ext != '.py': continue
      path = path_join(bin_dst_dir, stem.replace('_', '-')) # Omit extension from bin name.
      module = path_join(src_dir, stem).replace('/', '.')
      errSL(f'generating script for {module}: {path}')
      with open(path, 'w') as f:
        f.write(bin_template.format(py_path=py_path, module=module))
        chmod(f.fileno(), 0o755)


bin_template = '''\
#!{py_path}
# Generated by pithy/setup.py.
from {module} import main
main()
'''


def discover_packages():
  bad_names = []
  missing_inits = []
  for root in package_roots:
    for dir_path, dir_names, file_names in walk_path(root):
      yield dir_path
      dir_names[:] = filter(lambda n: n != '__pycache__', dir_names)
      for name in chain(dir_names, file_names):
        if '-' in name: bad_names.append(path_join(dir_path, name))
      if '__init__.py' not in file_names:
        missing_inits.append(path_join(dir_path, '__init__.py'))

  if bad_names: errSL(f'bad module names:\n' + '\n'.join(sorted(bad_names)))
  if missing_inits: errSL(f'missing package files:\n' + '\n'.join(sorted(missing_inits)))
  if bad_names or missing_inits: exit(1)



packages = list(discover_packages())
print('packages:', *packages)

setup(
  cmdclass={
    'build_scripts': BuildScripts,
    'develop': Develop,
    'install': Install,
  },
  packages=packages,
  py_modules=modules,
)
