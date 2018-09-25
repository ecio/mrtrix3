# Collection of convenience functions for manipulating files and directories, as well as filesystem paths



# List the content of a directory
def allInDir(directory, dir_path=True, ignore_hidden_files=True): #pylint: disable=unused-variable
  import ctypes, os
  from mrtrix3 import isWindows
  def is_hidden(directory, filename):
    if isWindows():
      try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(u"%s" % str(os.path.join(directory, filename)))
        assert attrs != -1
        return bool(attrs & 2)
      except (AttributeError, AssertionError):
        return filename.startswith('.')
    return filename.startswith('.')
  flist = sorted([filename for filename in os.listdir(directory) if not ignore_hidden_files or not is_hidden(directory, filename) ])
  if dir_path:
    return [ os.path.join(directory, filename) for filename in flist ]
  return flist



# Determines the common postfix for a list of filenames (including the file extension)
def commonPostfix(inputFiles): #pylint: disable=unused-variable
  from mrtrix3 import app
  first = inputFiles[0]
  cursor = 0
  found = False
  common = ''
  for dummy_i in reversed(first):
    if not found:
      for j in inputFiles:
        if j[len(j)-cursor-1] != first[len(first)-cursor-1]:
          found = True
          break
      if not found:
        common = first[len(first)-cursor-1] + common
      cursor += 1
  app.debug('Common postfix of ' + str(len(inputFiles)) + ' is \'' + common + '\'')
  return common



# This function can (and should in some instances) be called upon any file / directory
#   that is no longer required by the script. If the script has been instructed to retain
#   all temporaries, the resource will be retained; if not, it will be deleted (in particular
#   to dynamically free up storage space used by the script).
def delTemporary(path): #pylint: disable=unused-variable
  import shutil, os
  from mrtrix3 import app
  if not app.cleanup:
    return
  if isinstance(path, list):
    if len(path) == 1:
      delTemporary(path[0])
      return
    if app.verbosity > 2:
      app.console('Deleting ' + str(len(path)) + ' temporary items: ' + str(path))
    for entry in path:
      if os.path.isfile(entry):
        func = os.remove
      elif os.path.isdir(entry):
        func = shutil.rmtree
      else:
        continue
      try:
        func(entry)
      except OSError:
        pass
    return
  if os.path.isfile(path):
    temporary_type = 'file'
    func = os.remove
  elif os.path.isdir(path):
    temporary_type = 'directory'
    func = shutil.rmtree
  else:
    app.debug('Unknown target \'' + path + '\'')
    return
  if app.verbosity > 2:
    app.console('Deleting temporary ' + temporary_type + ': \'' + path + '\'')
  try:
    func(path)
  except OSError:
    app.debug('Unable to delete temporary ' + temporary_type + ': \'' + path + '\'')



# Get the full absolute path to a user-specified location.
#   This function serves two purposes:
#   To get the intended user-specified path when a script is operating inside a temporary directory, rather than
#     the directory that was current when the user specified the path;
#   To add quotation marks where the output path is being interpreted as part of a full command string
#     (e.g. to be passed to run.command()); without these quotation marks, paths that include spaces would be
#     erroneously split, subsequently confusing whatever command is being invoked.
def fromUser(filename, is_command): #pylint: disable=unused-variable
  import os, shlex
  from mrtrix3 import app
  fullpath = os.path.abspath(os.path.join(app.workingDir, filename))
  if is_command:
    fullpath = shlex.quote(fullpath)
  app.debug(filename + ' -> ' + fullpath)
  return fullpath



# Make a directory if it doesn't exist; don't do anything if it does already exist
def makeDir(path): #pylint: disable=unused-variable
  import errno, os
  from mrtrix3 import app
  try:
    os.makedirs(path)
    app.debug('Created directory ' + path)
  except OSError as exception:
    if exception.errno != errno.EEXIST:
      raise
    app.debug('Directory \'' + path + '\' already exists')



# Get an appropriate location and name for a new temporary file / directory
# Note: Doesn't actually create anything; just gives a unique name that won't over-write anything
def newTemporary(suffix): #pylint: disable=unused-variable
  import os.path, random, string
  from mrtrix3 import app, config
  dir_path = config['TmpFileDir'] if 'TmpFileDir' in config else (app.tempDir if app.tempDir else os.getcwd())
  prefix = config['TmpFilePrefix'] if 'TmpFilePrefix' in config else 'mrtrix-tmp-'
  full_path = dir_path
  suffix = suffix.lstrip('.')
  while os.path.exists(full_path):
    random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
    full_path = os.path.join(dir_path, prefix + random_string + '.' + suffix)
  app.debug(full_path)
  return full_path



# Determine the name of a sub-directory containing additional data / source files for a script
# This can be algorithm files in lib/mrtrix3, or data files in /share/mrtrix3/
def scriptSubDirName(): #pylint: disable=unused-variable
  import inspect, os
  from mrtrix3 import app
  frameinfo = inspect.stack()[-1]
  try:
    frame = frameinfo.frame
  except: # Prior to Version 3.5
    frame = frameinfo[0]
  # If the script has been run through a softlink, we need the name of the original
  #   script in order to locate the additional data
  name = os.path.basename(os.path.realpath(inspect.getfile(frame)))
  if not name[0].isalpha():
    name = '_' + name
  app.debug(name)
  return name



# Find data in the relevant directory
# Some scripts come with additional requisite data files; this function makes it easy to find them.
# For data that is stored in a named sub-directory specifically for a particular script, this function will
#   need to be used in conjunction with scriptSubDirName()
def sharedDataPath(): #pylint: disable=unused-variable
  import os
  from mrtrix3 import app
  result = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, 'share', 'mrtrix3')))
  app.debug(result)
  return result



# Get the full absolute path to a location in the temporary script directory
# Also deals with the potential for special characters in a path (e.g. spaces) by wrapping in quotes
def toTemp(filename, is_command): #pylint: disable=unused-variable
  import os, shlex
  from mrtrix3 import app
  fullpath = os.path.abspath(os.path.join(app.tempDir, filename))
  if is_command:
    fullpath = shlex.quote(fullpath)
  app.debug(filename + ' -> ' + fullpath)
  return fullpath



# Wait until a particular file not only exists, but also does not have any
#   other process operating on it (so hopefully whatever created it has
#   finished its work)
# This functionality is achieved in different ways, depending on the capabilities
#   of the system:
#   - On Windows, two processes cannot open the same file in read mode. Therefore,
#     try to open the file in 'rb+' mode, which requests write access but does not
#     create a new file if none exists
#   - If command fuser is available, use it to test if any processes are currently
#     accessing the file (note that since fuser's silent mode is used and a decision
#     is made based on the return code, other processes accessing the file will
#     result in the script pausing regardless of whether or not those processes have
#     write mode access)
#   - If neither of those applies, no additional safety check can be performed.
# Initially, checks for the file once every 1/1000th of a second; this gradually
#   increases if the file still doesn't exist, until the program is only checking
#   for the file once a minute.
def waitFor(paths): #pylint: disable=unused-variable
  import os, time
  from mrtrix3 import app, isWindows

  def inUse(path):
    import subprocess
    from distutils.spawn import find_executable
    if not os.path.isfile(path):
      return None
    if isWindows():
      if not os.access(path, os.W_OK):
        return None
      try:
        with open(path, 'rb+') as dummy_f:
          pass
        return False
      except:
        return True
    if not find_executable('fuser'):
      return None
    # fuser returns zero if there IS at least one process accessing the file
    # A fatal error will result in a non-zero code -> inUse() = False, so waitFor() can return
    return not subprocess.call(['fuser', '-s', path], shell=False, stdin=None, stdout=None, stderr=None)

  def numExist(data):
    count = 0
    for entry in data:
      if os.path.exists(entry):
        count += 1
    return count

  def numInUse(data):
    count = 0
    valid_count = 0
    for entry in data:
      result = inUse(entry)
      if result:
        count += 1
      if result is not None:
        valid_count += 1
    if not valid_count:
      return None
    return count

  # Make sure the data we're dealing with is a list of strings;
  #   or make it a list of strings if it's just a single entry
  if isinstance(paths, str):
    paths = [ paths ]
  else:
    assert isinstance(paths, list)
    for entry in paths:
      assert isinstance(entry, str)

  app.debug(str(paths))

  # Wait until all files exist
  num_exist = numExist(paths)
  if num_exist != len(paths):
    progress = app.progressBar('Waiting for creation of ' + (('new item \"' + paths[0] + '\"') if len(paths) == 1 else (str(len(paths)) + ' new items')), len(paths))
    for _ in range(num_exist):
      progress.increment()
    delay = 1.0/1024.0
    while not num_exist == len(paths):
      time.sleep(delay)
      new_num_exist = numExist(paths)
      if new_num_exist == num_exist:
        delay = max(60.0, delay*2.0)
      elif new_num_exist > num_exist:
        for _ in range(new_num_exist - num_exist):
          progress.increment()
        num_exist = new_num_exist
        delay = 1.0/1024.0
    progress.done()
  else:
    app.debug('Item' + ('s' if len(paths) > 1 else '') + ' existed immediately')

  # Check to see if active use of the file(s) needs to be tested
  at_least_one_file = False
  for entry in paths:
    if os.path.isfile(entry):
      at_least_one_file = True
      break
  if not at_least_one_file:
    app.debug('No target files, directories only; not testing for finalization')
    return

  # Can we query the in-use status of any of these paths
  num_in_use = numInUse(paths)
  if num_in_use is None:
    app.debug('Unable to test for finalization of new files')
    return

  # Wait until all files are not in use
  if not num_in_use:
    app.debug('Item' + ('s' if len(paths) > 1 else '') + ' immediately ready')
    return

  progress = app.progressBar('Waiting for finalization of ' + (('new file \"' + paths[0] + '\"') if len(paths) == 1 else (str(len(paths)) + ' new files')))
  for _ in range(len(paths) - num_in_use):
    progress.increment()
  delay = 1.0/1024.0
  while num_in_use:
    time.sleep(delay)
    new_num_in_use = numInUse(paths)
    if new_num_in_use == num_in_use:
      delay = max(60.0, delay*2.0)
    elif new_num_in_use < num_in_use:
      for _ in range(num_in_use - new_num_in_use):
        progress.increment()
      num_in_use = new_num_in_use
      delay = 1.0/1024.0
  progress.done()