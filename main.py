# main.py
import tkinter as tk
from gui import GuitarScrollPlayerGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = GuitarScrollPlayerGUI(root)
    root.mainloop()