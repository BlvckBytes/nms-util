import os
import pathlib
import tabulate

from java_class import JavaClass

java_file_cache = {}

'''
Checks if a file path matches search words
'''
def does_path_match(file, search):
  file_name = os.path.basename(file.absolute()).lower()
  return all(
    map(lambda x: x.lower() in file_name, search)
  )

'''
Get a list of matching class file paths by searching
a list of words within a class' name
'''
def find_matches(path, search):
  files = java_file_cache[path] if path in java_file_cache else None

  # Initially populate the file cache for this path
  if not files:
    files = list(pathlib.Path(path).rglob('*.java'))
    java_file_cache[path] = files

  return list(filter(lambda file: does_path_match(file, search), files))

'''
Main entry point of this command
'''
def invoke(existing_versions, identifier_to_version, args):
  if len(args) == 0:
    print('Please provide at least one word.')
    return

  table = []

  for version in existing_versions:
    version_path = existing_versions[version]
    matches = find_matches(version_path, args)

    for match in matches:

      with open(match, 'r') as f:
        contents = f.readlines()
        jcl = JavaClass(str(match), contents)

        if jcl.not_a_class == True:
          continue

        table.append([version, jcl.package, jcl.class_name, ', '.join(jcl.fields)])

  print()
  print(tabulate.tabulate(
    table, headers=['version', 'package', 'class', 'fields'],
    tablefmt='pretty', numalign='left', stralign='left'
  ))