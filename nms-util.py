import os
import os.path
import subprocess
import hashlib
import sys
import signal
import json
import git
import io
import re

from commands import search

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
  existing = dict(sorted(find_existing_decompiles().items(), key=lambda x: calculate_version_weight(x[0])))

  if len(existing) == 0:
    print('There are no versions available yet, please invoke build-tools at least once.')
    sys.exit()

  # Register all available commands here
  commands = {
    'search': search
  }

  # Query all available versions for matching classes
  while True:
    command_str = input('\nEnter command: ')
    command_data = command_str.split(' ')
    command = command_data[0]

    if command not in commands:
      print('Unknown command, use any of: ' + ','.join(commands.keys()))
      continue

    commands[command].invoke(existing, identifier_to_version, command_data[1:])

if __name__ == '__main__':
  main()