RMBG is a really useful utility for background removal. I have RMBG installed on this computer with its own virtual environment.

What would be really useful to make it easier to use would be the following: If I am navigating a directory in Dolphin, the file manager in KDE, and I come across an image that I want to remove the background for, I could right-click and then select "Quick RMBG" from the context menu.

Quick RMBG would be a CLI wrapper around RMBG. If I selected it, the script would take the image, run it through RMBG, and then save the output with `_nobg` while preserving the original. It would simply display a success message: "Background removed." The actual user interface would be entirely within the file manager.