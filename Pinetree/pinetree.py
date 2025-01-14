import os
import tkinter as tk
from tkinter import ttk, messagebox

def create_folders():
    """Creates the folder structure based on user input."""
    project_name = project_name_entry.get().strip()
    custom_folder_name = custom_folder_entry.get().strip()

    if not project_name:
        messagebox.showerror("Error", "Please enter a project name.")
        return

    # Determine the script directory and project path
    script_directory = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_directory, project_name)

    # Get selected folders from checkboxes
    selected_folders = [
        folder
        for folder, var in folder_vars.items()
        if var["var"].get()
    ]

    # Include custom folder if provided
    if custom_folder_name:
        selected_folders.append(custom_folder_name)

    if not selected_folders:
        messagebox.showerror("Error", "Please select at least one folder or enter a custom folder name.")
        return

    # Create the selected folder structure
    try:
        for folder in selected_folders:
            folder_path = os.path.join(project_path, *folder.split("/"))
            os.makedirs(folder_path, exist_ok=True)
        messagebox.showinfo("Success", f"Folders created successfully at:\n{project_path}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

def toggle_subfolders(parent, state):
    """Toggles the state of subfolders based on the parent folder."""
    for folder in folder_templates[selected_template]:
        if folder.startswith(parent + "/"):  # Check if it is a subfolder
            folder_vars[folder]["var"].set(state)
            folder_vars[folder]["checkbox"].state(["!disabled" if state else "disabled"])

def update_checkboxes():
    """Updates the checkboxes based on the selected template."""
    global folder_vars, selected_template
    folder_vars = {}

    # Clear existing checkboxes
    for widget in folder_frame.winfo_children():
        widget.destroy()

    # Populate new checkboxes for the selected template
    selected_template = template_var.get()
    for folder in folder_templates[selected_template]:
        indent = 20 * folder.count("/")  # Indentation based on folder depth
        is_parent = "/" not in folder or folder.count("/") == 1
        folder_vars[folder] = {
            "var": tk.BooleanVar(value=True),
            "checkbox": ttk.Checkbutton(
                folder_frame,
                text=folder.split("/")[-1],  # Display only the last part of the folder name
                variable=tk.BooleanVar(value=True)
            )
        }
        folder_vars[folder]["checkbox"] = ttk.Checkbutton(
            folder_frame,
            text=folder.split("/")[-1],
            variable=folder_vars[folder]["var"],
            command=(lambda f=folder: toggle_subfolders(f, folder_vars[f]["var"].get()))
            if is_parent else None,
        )
        folder_vars[folder]["checkbox"].pack(anchor="w", padx=indent + 10)
        if not is_parent:  # Initially disable subfolders
            folder_vars[folder]["checkbox"].state(["disabled"])

# Define folder templates with hierarchical structure
folder_templates = {
    "MoGr": ["assets", "proj", "export"],
    "3D": [
        "assets",
        "mat", "mat/substance", "mat/textures", "mat/combined",
        "geo", "geo/z",
    ]
}

# Initialize folder_vars globally
folder_vars = {}
selected_template = "MoGr"

# Set up the main application window
root = tk.Tk()
root.title("Project Folder Wizard")
root.geometry("350x500")
root.resizable(False, False)

# Project Name Input
ttk.Label(root, text="Project Name:").pack(pady=5, anchor="w", padx=10)
project_name_entry = ttk.Entry(root, width=30)
project_name_entry.pack(pady=5, padx=10)

# Template Selection
ttk.Label(root, text="Folder Template:").pack(pady=5, anchor="w", padx=10)
template_var = tk.StringVar(value="MoGr")

ttk.Radiobutton(root, text="MoGr", variable=template_var, value="MoGr", command=update_checkboxes).pack(anchor="w", padx=20)
ttk.Radiobutton(root, text="3D", variable=template_var, value="3D", command=update_checkboxes).pack(anchor="w", padx=20)

# Frame for folder checkboxes
ttk.Label(root, text="Select Folders:").pack(pady=5, anchor="w", padx=10)
folder_frame = ttk.Frame(root)
folder_frame.pack(fill="both", expand=True, padx=10)

# Custom Folder Input
ttk.Label(root, text="Custom Folder (Optional):").pack(pady=5, anchor="w", padx=10)
custom_folder_entry = ttk.Entry(root, width=30)
custom_folder_entry.pack(pady=5, padx=10)

# Button to Create Folders
ttk.Button(root, text="Create Folders", command=create_folders).pack(pady=10)

# Initialize the folder checkboxes for the default template
update_checkboxes()

# Run the application
root.mainloop()
