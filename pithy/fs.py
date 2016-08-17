# Dedicated to the public domain under CC0: https://creativecommons.org/publicdomain/zero/1.0/.

import os as _os
import os.path as _path
import shutil as _shutil
import stat as _stat

from itertools import zip_longest as _zip_longest


# paths.

def executable_path():
  'Return the path to this executable.'
  import __main__
  return _path.realpath(__main__.__file__)

def executable_dir():
  'Return the parent directory of this excutable.'
  return _path.dirname(executable_real_path())

def is_path_abs(path):
  'Return true if the path is an absolute path.'
  return _path.isabs(path)

def normalize_path(path):
  'Normalize the path according to system convention.'
  return _path.normpath(path)

def rel_path(path, start='.'):
  'Return a path relative to start, defaulting to the current directory.'
  return _path.relpath(path, start)

def path_common_prefix(*paths):
  'Return the common prefix of a sequence of paths.'
  return _path.commonprefix(paths)

def path_dir(path):
  "Return the dir portion of a path (possibly empty), e.g. 'dir/name'."
  return _path.dirname(path)

def path_dir_or_dot(path):
  "Return the dir portion of a path, e.g. 'dir/name', or '.' in the case of no path."
  return path_dir(path) or '.'

def path_join(*items):
  'Join the path with the system path separator.'
  return _path.join(*items)

def path_name(path):
  "Return the name portion of a path (possibly including an extension), e.g. 'dir/name'."
  return _path.basename(path)

def path_range(start_path, end_path):
  'Yield a sequence of paths from start_path (inclusive) to end_path (exclusive).'
  # TODO: more descriptive name.
  start = path_split(start_path)
  end = path_split(end_path)
  accum = []
  for s, e in _zip_longest(start, end):
    if s:
      if s != e:
        raise ValueError('paths diverge: start {!r}; end: {!r}'.format(s, e))
    else:
      yield path_join(*accum)
    accum.append(e)

def path_rel_to(base, path):
  'Return the path relative to the base, raising an exception the path does not have that base.'
  if not path.startswith(base):
    raise ValueError('path expected to have prefix: {}; actual: {}'.format(base, path))
  return path[len(base):]

def path_split(path):
  np = normalize_path(path)
  if np == '/': return ['/']
  assert not np.endswith('/')
  return [comp or '/' for comp in np.split(_os.sep)]

def path_stem(path):
  'The path without the file extension; the stem may span multiple directories.'
  return split_stem_ext(path)[0]

def path_ext(path):
  'The file extension of the path.'
  return split_stem_ext(path)[1]

def path_name_stem(path):
  'The file name without extension; the name stem will not span directories.'
  return path_stem(path_name(path))

def split_dir_name(path):
  "Split the path into dir and name (possibly including an extension) components, e.g. 'dir/name'."
  return _path.split(path)

def split_dir_stem_ext(path):
  'Split the path into a (dir, stem, ext) triple.'
  dir, name = split_dir_name(path)
  stem, ext = split_stem_ext(name)
  return dir, stem, ext

def split_stem_ext(path):
  '''
  Split the path into stem (possibly spanning directories) and extension components, e.g. 'stem.ext'.
  '''
  return _path.splitext(path)

def append_path_stem_suffix(path, suffix):
  'Append suffix to the path stem.'
  stem, ext = split_stem_ext(path)
  return stem + suffix + ext

# file system.

def abs_path(path): return _path.abspath(path)

def abs_or_normalize_path(path, make_abs):
  'Returns the absolute path if make_abs is True, if make_abs is False, returns a normalized path.'
  return abs_path(path) if make_abs else normalize_path(path)

def copy_file(src, dst, follow_symlinks=True):
  'Copies file from source to destination.'
  _shutil.copy(src, dst, follow_symlinks=follow_symlinks)

def copy_dir_tree(src, dst, follow_symlinks=True, preserve_metadata=True, ignore_dangling_symlinks=False):
  'Copies a directory tree.'
  _shutil.copytree(src, dst,
    symlinks=(not follow_symlinks),
    ignore=None,
    copy_function=(_shutil.copy2 if preserve_metadata else _shutil.copy),
    ignore_dangling_symlinks=ignore_dangling_symlinks)


def expand_user(path): return _path.expanduser(path)

def is_dir(path): return _path.isdir(path)

def is_file(path): return _path.isfile(path)

def is_link(path): return _path.islink(path)

def is_mount(path): return _path.ismount(path)

def link_exists(path): return _path.lexists(path)

def list_dir(path): return _os.listdir(path)

def list_dir_paths(path): return [path_join(path, name) for name in list_dir(path)]

def make_dir(path): return _os.mkdir(path)

def make_dirs(path, mode=0o777, exist_ok=True): return _os.makedirs(path, mode, exist_ok)

def path_exists(path): return _path.exists(path)

def remove_file(path): return _os.remove(path)

def remove_file_if_exists(path):
  if is_file(path):
    remove_file(path)

def remove_dir(path): return _os.rmdir(path)

def remove_dirs(path): return _os.removedirs(path)

def current_dir(): return abs_path('.')

def parent_dir(): return abs_path('..')

def change_dir(path): _os.chdir(path)

def file_time_access(path): return _os.stat(path).st_atime

def file_time_mod(path): return _os.stat(path).st_mtime

def file_time_meta_change(path): return _os.stat(path).st_ctime

def file_size(path): return _os.stat(path).st_size

def file_permissions(path): return _os.stat(path).st_mode

def is_file_not_link(path): return is_file(path) and not is_link(path)

def is_dir_not_link(path): return is_dir(path) and not is_link(path)


def is_python3_file(path, always_read=False):
  '''
  heuristics to decide if a file is a python script.
  TODO: support zip archives.
  '''
  if not always_read:
    ext = path_ext(path)
    if ext: return ext == '.py'
  try:
    with open(path, 'rb') as f:
      expected = b'#!/usr/bin/env python3\n'
      head = f.read(len(expected))
      return head == expected
  except FileNotFoundError: return False


def add_file_execute_permissions(path):
  old_perms = file_permissions(path)
  new_perms = old_perms | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH
  _os.chmod(path, new_perms)

def remove_dir_contents(path):
  if _path.islink(path): raise OSError('remove_dir_contents received symlink: ' + path)
  l = _os.listdir(path)
  for n in l:
    p = _path.join(path, n)
    if _path.isdir(p) and not _path.islink(p):
      remove_dir_tree(p)
    else:
      _os.remove(p)


def remove_dir_tree(path):
  remove_dir_contents(path)
  _os.rmdir(path)


def move_file(path, dest, overwrite=False):
  if path_exists(dest) and not overwrite:
    raise OSError('destination path already exists: '.format(dest))
  _os.rename(path, dest)


def _walk_dirs_and_files(dir_path, include_hidden, file_exts, files_as_paths):
  sub_dirs = []
  files = []
  names = list_dir(dir_path)
  for name in names:
    if not include_hidden and name.startswith('.'):
      continue
    path = path_join(dir_path, name)
    if is_dir(path):
      sub_dirs.append(path)
    elif file_exts is None or path_ext(name) in file_exts:
      files.append(path if files_as_paths else name)
  yield (dir_path + '/', files)
  for sub_dir in sub_dirs:
    yield from _walk_dirs_and_files(sub_dir, include_hidden, file_exts, files_as_paths)


def walk_dirs_and_files(*dir_paths, make_abs=False, include_hidden=False, file_exts=None,
  files_as_paths=False):
  '''
  yield (dir_path, files) pairs.
  files is an array of either names (default) or paths, depending on the files_as_paths option.
  '''
  assert not isinstance(file_exts, str) # exts should be a sequence of strings.
  assert file_exts is None or all(e.startswith('.') for e in file_exts) # all extensions should begin with a dot.

  for raw_path in dir_paths:
    dir_path = abs_or_normalize_path(raw_path, make_abs)
    yield from _walk_dirs_and_files(dir_path, include_hidden, file_exts, files_as_paths)


def _walk_paths_rec(dir_path, yield_files, yield_dirs, include_hidden, file_exts):
  'yield paths; directory paths are distinguished by trailing slash.'
  if yield_dirs:
    yield dir_path + '/'
  names = list_dir(dir_path)
  for name in names:
    if not include_hidden and name.startswith('.'):
      continue
    path = path_join(dir_path, name)
    if is_dir(path):
      yield from _walk_paths_rec(path, yield_files, yield_dirs, include_hidden, file_exts)
    elif yield_files and (file_exts is None or path_ext(name) in file_exts):
      yield path

def walk_paths(*paths, make_abs=False, yield_files=True, yield_dirs=True, include_hidden=False,
  file_exts=None):
  '''
  generate file and/or dir paths,
  optionally filtering hidden names and/or by file extension.
  '''
  assert not isinstance(file_exts, str) # exts should be a sequence of strings.
  assert file_exts is None or all(e.startswith('.') for e in file_exts) # all extensions should begin with a dot.

  for raw_path in paths:
    path = abs_or_normalize_path(raw_path, make_abs)
    if is_dir(path):
      yield from _walk_paths_rec(path, yield_files, yield_dirs, include_hidden, file_exts)
    elif not path_exists(path):
      raise FileNotFoundError(path)
    elif yield_files and (file_exts is None or path_ext(path) in file_exts):
      yield path


def walk_files(*paths, make_abs=False, include_hidden=False, file_exts=None):
  return walk_paths(*paths, make_abs=make_abs, yield_files=True, yield_dirs=False,
    include_hidden=include_hidden, file_exts=file_exts)


def walk_dirs(*paths, make_abs=False, include_hidden=False, file_exts=None):
  return walk_paths(*paths, make_abs=make_abs, yield_files=False, yield_dirs=True,
    include_hidden=include_hidden, file_exts=file_exts)


def walk_dirs_up(path):
  ap = abs_path(path)
  dir_path = ap if is_dir(ap) else path_dir(ap)
  while True:
    yield dir_path
    if dir_path == '/':
      break
    dir_path = path_dir(dir_path)
