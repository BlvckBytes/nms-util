import os
import os.path
import subprocess
import hashlib
import pathlib
import sys
import signal
import json
import git
import io
import re

from java_class import JavaClass

# Location of the build tools folder where caches are kept
buildtools_path = '/Users/blvckbytes/Documents/Tools/BuildTools'
buildtools_work_path = buildtools_path + '/work'

# URL of the build data repository
builddata_url = 'https://hub.spigotmc.org/stash/scm/spigot/builddata.git'

# Path of the temporary repo clone
fetch_repo_path = '/tmp/builddata'

# Command to only clone .git
fetch_repo_cmd = f'git clone --filter=blob:none --no-checkout --single-branch --branch master {builddata_url} {fetch_repo_path}'

# Command to be executed to receive <commit-hash> <commit message> for each commit
retrieve_log_cmd = 'git --no-pager log --decorate=no --no-color --pretty=oneline'

# Caching results of parsing commit logs
identifier_to_version = {}

# Caching results of listing paths recursively for .java files
java_file_cache = {}

'''
Tries to resolve an identifier (substring of a hashed commit hash)
into it's corresponding minecraft-version (from the commit-message).
'''
def resolve_identifier_to_version(identifier):
  global identifier_to_version

  if len(identifier_to_version.keys()) == 0:
    print('Loading commits...')

    # Initially clone the repo
    if not os.path.exists(fetch_repo_path):
      process = subprocess.Popen(fetch_repo_cmd, shell=True, stdout=subprocess.PIPE)
      process.wait()

    # Run log retrieval command inside repo
    process = subprocess.Popen(f'cd {fetch_repo_path} && {retrieve_log_cmd}', shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0].decode('utf-8')

    for line in output.split('\n'):

      if line.strip() == '':
        continue

      commit_hash = line[:line.index(' ')]
      commit_message = line[line.index(' ') + 1:]

      # Rehash the commit hash
      commit_hash_hash = hashlib.md5(commit_hash.encode('utf-8')).hexdigest()

      repo = git.Repo(fetch_repo_path)
      commit = repo.commit(commit_hash)

      try:
        target_file = commit.tree / 'info.json'

        with io.BytesIO(target_file.data_stream.read()) as f:
          json_val = json.load(f)
          id_val = commit_hash_hash[24:]
          version = json_val['minecraftVersion']

          identifier_to_version[id_val] = version

      except KeyError:
        pass

  return identifier_to_version[identifier] if identifier in identifier_to_version else None

'''
Calculates a numeric (floating point) weight of a
version notation for sorting purposes
'''
def calculate_version_weight(version):
  numbers = re.split(r'\.|-', version)
  score = 0

  for i in range(0, min(3, len(numbers))):
    number = numbers[i].replace('pre', '')
    try:
      # Each 'more minor' version number weighs less
      score += int(number) * 10**(4 - i)
    except ValueError:
      continue

  return score

'''
Look at all existing decompile source folders inside of
build tools and try to assign a version to each of them.
'''
def find_existing_decompiles():
  results = {}

  for name in os.listdir(buildtools_work_path):
    curr_path = os.path.join(buildtools_work_path, name)

    # Target decompile output dirs
    if not name.startswith('decompile'):
      continue

    # Not a dir, just making sure
    if not os.path.isdir(curr_path):
      continue

    identifier = name[name.index('-') + 1:]

    # Latest is relative...
    if identifier == 'latest':
      continue

    ver = resolve_identifier_to_version(identifier)

    # Could not determine version
    if not ver:
      print(f'Could not find a version for {identifier}')
      continue

    results[ver] = curr_path

  # Not as many decompiles available as versions exist
  if len(results) != len(identifier_to_version):
    print('You could still download: ')
    for ind, version in enumerate(sorted(set(identifier_to_version.values()), key=calculate_version_weight)):
      if not version in results:
        print(f'{"" if ind == 0 else ", "}{version}', end="")
    print()

  return results

'''
Prompt for a number by printing a prompt each time until a
valid number between inside of [min;max] has been entered.
'''
def prompt_for_number(prompt, min, max):
  while True:
    choice = None
    try:
      choice = int(input(prompt))
    except ValueError:
      choice = None

    if choice is None or choice < min or choice > max:
      print('Invalid choice, retry.')
    else:
      return choice

'''
Checks if a file path matches search words
'''
def does_path_match(file, search):
  file_name = os.path.basename(file.absolute()).lower()
  return all(
    map(lambda x: x.lower() in file_name, search)
  )

def find_matches(path, search):
  files = java_file_cache[path] if path in java_file_cache else None

  # Initially populate the file cache for this path
  if not files:
    files = list(pathlib.Path(path).rglob('*.java'))
    java_file_cache[path] = files

  return list(filter(lambda file: does_path_match(file, search), files))

'''
Prompt for a valid class (.java file) by providing a fuzzy finder.
'''
def prompt_for_class(path):

  search = input('\nClass search: ').lower().split(' ')
  matches = find_matches(path, search)

  # No matches
  if len(matches) == 0:
    return None

  # Only a single match
  if len(matches) == 1:
    return matches[0]

  # Print choice screen

  print('There are multiple resutls:')
  for i in range(0, len(matches)):
    print(f'[{i}]: {matches[i]}')

  choice = prompt_for_number('Select a class: ', 0, len(matches) - 1)
  return matches[choice]

'''
Handles the SIGINT control signal
'''
def on_forceful_program_exit(signal, frame):
  print('\nBye!')
  sys.exit(0)

'''
Main entry point of this program.
'''
def main():
  signal.signal(signal.SIGINT, on_forceful_program_exit)

  print('Detecting available decompiled versions...')
  existing = find_existing_decompiles()
  existing_keys = list(sorted(existing.keys(), key=calculate_version_weight))
  num_existing_keys = len(existing_keys)

  if num_existing_keys == 0:
    print('There are no versions available yet, please invoke build-tools at least once.')
    sys.exit()

  # Print version choice screen
  # print('Available versions:')
  # for i in range(0, num_existing_keys):
  #   curr_key = existing_keys[i]

  #   print(f'[{i}] -> {curr_key}')
  
  # # Prompt until a proper version has been entered
  # choice = prompt_for_number('Select a version: ', 0, num_existing_keys - 1)
  # selected_version = existing_keys[choice]

  # print(f'Selected version {selected_version}.')

  # Prompt for classes to look up
  # while True:
  #   class_path = prompt_for_class(existing[selected_version])

  #   # Dump class contents to screen
  #   print(f'Contents of class {os.path.basename(class_path)}:\n')
  #   with open(class_path, 'r') as f:
  #     for line in f.readlines():
  #       print(line, sep='')

  #   print()

  version_spacer_len = 50

  # Query all available versions for matching classes
  while True:
    search = input('\nEnter class search term: ').lower().split(' ')

    for version in existing_keys:
      version_path = existing[version]
      matches = find_matches(version_path, search)

      content = f'{version} ' + ('NO MATCHES' if len(matches) == 0 else '')
      content += '-' * (version_spacer_len - len(content))
      print(content)

      for match in matches:
        with open(match, 'r') as f:
          contents = f.readlines()
          print(JavaClass(str(match), contents))

if __name__ == '__main__':
  main()