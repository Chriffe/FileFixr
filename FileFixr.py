# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading
import string
import re

def generate_log_filename(log_directory, base_name):
    """Creates a log file name with a timestamp in the given log directory."""
    timecode = datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(log_directory, f"{base_name}-{timecode}.txt")

def log_changes(log_filename, message, mode='a'):
    """Writes changes to the log file."""
    with open(log_filename, mode, encoding='utf-8') as log_file:
        log_file.write(message + '\n')

def sanitize_filename(filename):
    # Characters to be replaced with a hyphen
    replace_with_hyphen = ':/\\~'
    
    # Allowed characters including Nordic and other European characters
    valid_chars = "&-_.() " + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789åäöüøÅÄÖÜØéáíóúÉÁÍÓÚñÑçÇäÄåÅöÖüÜøØ"
    
    # Replace specific characters with hyphen
    for char in replace_with_hyphen:
        filename = filename.replace(char, '-')
    
    # Remove characters that are not in the list of valid characters
    filename = ''.join(char for char in filename if char in valid_chars)
    
    # Split the filename into base and extension
    base, ext = os.path.splitext(filename)
    
    # Remove leading and trailing spaces from the base part of the filename
    base = base.strip()
    
    # Reduce multiple consecutive dots to one and remove trailing dot if no file extension
    new_base = re.sub(r'\.+', '.', base).rstrip('.')
    
    # Return the sanitized filename
    return new_base + ext

def sanitize_directory_name(directory_name):
    """Sanitizes the directory name by removing leading and trailing spaces."""
    return directory_name.strip()

def rename_entity(original_path, new_path, dry_run, renamed_entities, change_list):
    """Renames a file or directory and adds the change to a list, adding a number to the name if it already exists."""
    original_base_name = os.path.basename(original_path)
    new_base_name = os.path.basename(new_path)
    
    if original_base_name != new_base_name:
        base, ext = os.path.splitext(new_path)
        unique_new_path = new_path  # Initialize with intended new path
        counter = 1
        # Check if the new (unique) path exists and modify it until it doesn't
        while os.path.exists(unique_new_path):
            unique_new_path = f"{base}_{counter}{ext}"
            counter += 1
        
        # Update new_base_name with the final unique name
        new_base_name = os.path.basename(unique_new_path)
        
        if not dry_run:
            try:
                os.rename(original_path, unique_new_path)
                renamed_entities[unique_new_path] = original_path  # Track successful rename
                change_list.append(f"'{original_base_name}' was renamed to '{new_base_name}'\n")
                return True  # Indicate that a rename occurred
            except OSError as e:
                change_list.append(f"ERROR: Could not rename '{original_base_name}' to '{new_base_name}': {e}\n")
        else:
            change_list.append(f"'{original_base_name}' would be renamed to '{new_base_name}'\n")
    return False  # Indicate no rename occurred if names are the same or in case of dry run without action

def rename_entities_in_directory(directory, include_subdirs, dry_run, log_filename, progress_var, status_label):
    renamed_entities = {}
    change_list = []
    file_count = 0  # No need for a list
    dir_count = 0

    # Calculate total entities for progress calculation
    total_files = sum(len(files) for _, _, files in os.walk(directory))
    total_dirs = sum(len(dirs) for _, dirs, _ in os.walk(directory)) if include_subdirs else 0
    total_entities = total_files + total_dirs

    progress_step = 100 / total_entities if total_entities > 0 else 0
    progress_var.set(0)  # Reset the progress bar

    # Iterate over each directory and file, and rename if necessary
    for root, dirs, files in os.walk(directory, topdown=False):
        # Process files
        for name in files:
            original_path = os.path.join(root, name)
            new_name = sanitize_filename(name)
            new_path = os.path.join(root, new_name)
            if rename_entity(original_path, new_path, dry_run, renamed_entities, change_list):
                file_count += 1  # Increment on successful rename
                progress_var.set(progress_var.get() + progress_step)

        # Process directories if included
        if include_subdirs:
            for name in dirs:
                original_path = os.path.join(root, name)
                sanitized_name = sanitize_directory_name(name)  # Sanitize the directory name
                new_name = sanitize_filename(sanitized_name)  # You can still apply filename sanitation rules if necessary
                new_path = os.path.join(root, new_name)
                if rename_entity(original_path, new_path, dry_run, renamed_entities, change_list):
                    dir_count += 1  # Increment on successful rename
                    progress_var.set(progress_var.get() + progress_step)

    progress_var.set(100)  # Complete the progress bar
    status_label.config(text="Inaktiv")

    # Log changes if any
    if change_list:
        log_changes(log_filename, ''.join(change_list))

    # Inform the user of the completed operation
    messagebox.showinfo("Finished", f"Changed {file_count} filenames and {dir_count} directories")

def start_thread(directory, include_subdirs, log_directory, dry_run, progress_var, status_label):
    # Generate the full path for the log file
    log_filename = generate_log_filename(log_directory, "dry_run_rename" if dry_run else "renamed_files_directories")
    threading.Thread(target=lambda: rename_entities_in_directory(directory, include_subdirs, dry_run, log_filename, progress_var, status_label), daemon=True).start()

def select_directory(entry):
    directory = filedialog.askdirectory()
    if directory:
        entry.delete(0, tk.END)
        entry.insert(0, directory)

def run(include_subdirs, dry_run, progress_var, status_label):
    source_dir = source_dir_entry.get()
    log_dir = log_dir_entry.get()
    progress_var.set(0)  # Reset the progress bar each time run is called
    status_label.config(text="Inactiv")  # Reset the status label each time run is called
    if not log_dir:
        messagebox.showerror("Error", "You must choose where to save the log file.")
        return
    if not os.path.isdir(log_dir):
        messagebox.showerror("Error", f"({log_dir}) is not a directory.")
        return
    log_filename = generate_log_filename(log_dir, "dry_run_rename" if dry_run else "renamed_files_directories")
    if dry_run:
        status_label.config(text="Söker...")
        start_thread(source_dir, include_subdirs.get(), log_dir, dry_run, progress_var, status_label)
    else:
        confirm = messagebox.askokcancel("Confirm", "Are you sure you want to remove invalid characters from file and directory names. This can cause unforseen problems.")
        if confirm:
            status_label.config(text="Searching and replacing...")
            start_thread(source_dir, include_subdirs.get(), log_dir, dry_run, progress_var, status_label)

# Set up the main application window
root = tk.Tk()
root.title("FileFixr")
root.resizable(False, False)

# Create a main frame
main_frame = ttk.Frame(root, padding="10")
main_frame.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Header text
header_label = ttk.Label(main_frame, text="FileFixr", font=("Arial Black", 25))
header_label.grid(column=0, row=0, columnspan=3, pady=(0, 10))

# Description text
description_label = ttk.Label(main_frame, text="This program removes invalid charcters from file and directory names.", font=("Segoe UI", 9))
description_label.grid(column=0, row=1, columnspan=3, pady=(0, 10))

# Directory to search
ttk.Label(main_frame, text="Directory to search:").grid(column=0, row=2, sticky=tk.W)
source_dir_entry = ttk.Entry(main_frame, width=50)
source_dir_entry.grid(column=0, row=3, columnspan=2, sticky=(tk.W, tk.E))
ttk.Button(main_frame, text="Add", command=lambda: select_directory(source_dir_entry)).grid(column=2, row=3)

# Include subdirectories checkbox
include_subdirs = tk.BooleanVar()
ttk.Checkbutton(main_frame, text="Include subdirectories", variable=include_subdirs).grid(column=0, row=4, columnspan=3, sticky=tk.W)

# Log file location
ttk.Label(main_frame, text="Path for log file:").grid(column=0, row=5, sticky=tk.W)
log_dir_entry = ttk.Entry(main_frame, width=50)
log_dir_entry.grid(column=0, row=6, columnspan=2, sticky=(tk.W, tk.E))
ttk.Button(main_frame, text="Add", command=lambda: select_directory(log_dir_entry)).grid(column=2, row=6)

# Progress bar and status label
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(main_frame, variable=progress_var, maximum=100, length=280)
progress_bar.grid(column=0, row=7, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
status_label = ttk.Label(main_frame, text="Inactiv")
status_label.grid(column=2, row=7, pady=(10, 0), sticky=tk.W)

# Run buttons
dry_run_button = ttk.Button(main_frame, text="Dry run", command=lambda: run(include_subdirs, True, progress_var, status_label))
dry_run_button.grid(column=0, row=8, pady=(10, 0), sticky=tk.W)
start_button = ttk.Button(main_frame, text="Start", command=lambda: run(include_subdirs, False, progress_var, status_label))
start_button.grid(column=2, row=8, pady=(10, 0), sticky=tk.E)

# Credit text
credit_label = ttk.Label(main_frame, text="GNU General Public License Version 3", font=("Segoe UI", 7))
credit_label.grid(column=0, row=9, columnspan=3, pady=(20, 0))

# Configure grid layout
main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Start the GUI event loop
root.mainloop()