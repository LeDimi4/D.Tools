import os
import tkinter as tk
from tkinter import ttk, messagebox

# Function to create folders
def create_folders():
    """Creates the folder structure based on user input."""
    # Retrieve user input for project name and custom folder name
    project_name = project_name_entry.get().strip()
    custom_folder_name = custom_folder_entry.get().strip()

    # Check if the project name is provided
    if not project_name:
        messagebox.showerror("Error", "Please enter a project name.")
        return

    # Determine the script directory and the project path
    script_directory = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_directory, project_name)

    # Collect selected folders from the checkboxes
    selected_folders = [
        folder
        for folder, var in folder_vars.items()
        if var["var"].get()
    ]

    # Include custom folder if specified
    if custom_folder_name:
        selected_folders.append(custom_folder_name)

    # Ensure at least one folder is selected
    if not selected_folders:
        messagebox.showerror("Error", "Please select at least one folder or enter a custom folder name.")
        return

    # Attempt to create the folder structure
    try:
        for folder in selected_folders:
            # Create nested folder paths
            folder_path = os.path.join(project_path, *folder.split("/"))
            os.makedirs(folder_path, exist_ok=True)

        # Notify the user of success
        messagebox.showinfo("Success", f"Folders created successfully at:\n{project_path}")
    except Exception as e:
        # Handle any errors that occur during folder creation
        messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

# Function to toggle subfolders
def toggle_subfolders(parent, state):
    """Toggles the state of subfolders based on the parent folder."""
    for folder in folder_templates:
        # Check if the folder is a subfolder of the parent
        if folder.startswith(parent + "/"):
            folder_vars[folder]["var"].set(state)
            folder_vars[folder]["checkbox"].state(["!disabled" if state else "disabled"])

# Function to update checkboxes
def update_checkboxes():
    """Updates the checkboxes based on the folder structure."""
    global folder_vars
    folder_vars = {}

    # Clear existing checkboxes from the frame
    for widget in folder_frame.winfo_children():
        widget.destroy()

    # Add new checkboxes for the folder structure
    for folder in folder_templates:
        indent = 20 * folder.count("/")  # Indentation reflects folder depth
        is_parent = "/" not in folder or folder.count("/") == 1

        # Define the checkbox and its associated variable
        folder_vars[folder] = {
            "var": tk.BooleanVar(value=True),
            "checkbox": ttk.Checkbutton(
                folder_frame,
                text=folder.split("/")[-1],  # Show only the last part of the folder name
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

        # Initially disable subfolders
        if not is_parent:
            folder_vars[folder]["checkbox"].state(["disabled"])

# Define folder templates with hierarchical structure
folder_templates = [
    "assets", "assets/downloaded",
    "proj",
    "export",
    "mat", "mat/substance", "mat/textures", "mat/combined",
    "geo", "geo/sculpt",
    "render"
]

# Initialize folder_vars globally
folder_vars = {}

# Set up the main application window
root = tk.Tk()
root.title("Project Folder Wizard")
root.geometry("200x500")  # Define the window size
root.resizable(False, False)  # Prevent resizing
root.configure(bg="#333333")  # Set background color

# Configure style for dark mode
style = ttk.Style()
style.configure("TLabel", background="#333333", foreground="#FFFFFF")
style.configure("TEntry", fieldbackground="#555555", foreground="#FFFFFF")
style.configure("TButton", background="#777777", foreground="#000000")
style.configure("TCheckbutton", background="#333333", foreground="#FFFFFF")
style.configure("TFrame", background="#333333")

# Project Name Input
ttk.Label(root, text="Project Name:").pack(pady=5, anchor="w", padx=10)
project_name_entry = ttk.Entry(root, width=25, style="TEntry")
project_name_entry.pack(pady=5, padx=15, anchor="w")

# Frame for folder checkboxes
ttk.Label(root, text="Select Folders:").pack(pady=5, anchor="w", padx=10)
folder_frame = ttk.Frame(root, style="TFrame")
folder_frame.pack(fill="both", expand=True, padx=10)

# Custom Folder Input
ttk.Label(root, text="Custom Folder (Optional):").pack(pady=5, anchor="w", padx=10)
custom_folder_entry = ttk.Entry(root, width=25, style="TEntry")
custom_folder_entry.pack(pady=5, padx=15, anchor="w")

# Button to Create Folders
create_button = ttk.Button(root, text="Create Folders", command=create_folders)
create_button.pack(pady=10, padx=15, anchor="w")
create_button.configure(width=25)

# Initialize the folder checkboxes
update_checkboxes()

# Run the application
root.mainloop()
