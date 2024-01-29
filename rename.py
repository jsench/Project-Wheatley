import os
import sys
import shutil

def rename_project(new_name):
    current_directory = os.getcwd()
    old_name = 'personcensus'

    # Rename the personcensus directory within the new name
    shutil.move(os.path.join(current_directory, old_name), os.path.join(current_directory, new_name + 'census'))

    # Recursively replace all instances of 'person' and 'person' with the new name
    for root, dirs, files in os.walk(new_name + 'census'):
        for filename in files:
            if filename == 'rename.py' or filename.startswith('.'):
                continue
            try:
                file_path = os.path.join(root, filename)
                with open(file_path, 'r') as file:
                    file_data = file.read()
                file_data = file_data.replace('person', new_name)
                file_data = file_data.replace('Person', new_name.capitalize())
                with open(file_path, 'w') as file:
                    file.write(file_data)
            except:
                continue

if __name__ == "__main__":
    print("Welcome\n")
    # Get name from user
    new_name = input("Please type the surname for your census...\n")
    # Strip spaces from name and render in lowercase (otherwise this would cause bugs)
    new_name = new_name.replace(' ', '').lower()

    rename_project(new_name)
    print(f"Great , project successfully renamed to '{new_name}census'.")
