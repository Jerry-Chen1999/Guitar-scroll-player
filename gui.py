# gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
from player import ImageScroller # Import the player logic


class GuitarScrollPlayerGUI:
    """
    Manages the Tkinter GUI for the Guitar Scroll Player.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("吉他谱滚动播放器")
        self.root.geometry("600x500") # Adjusted size for the listbox

        # --- Variables ---
        self.folder_path = tk.StringVar()
        self.speed = tk.DoubleVar(value=2.0) # Changed to DoubleVar for finer control
        self.play_mode = tk.StringVar(value=ImageScroller.MODE_SCROLL) # Default mode

        # Playback control variables
        self.scroll_thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_paused = False # Track pause state for UI
        self.is_stopping = False

        # --- FIXED: Define the relative path to Sheet_Music ---
        # This assumes gui.py is in the same directory as the Sheet_Music folder
        # when the script is run.
        if getattr(sys, 'frozen', False):
            # If running as a PyInstaller bundle, the base path is _MEIPASS
            base_path = sys._MEIPASS
        else:
            # If running as a script, the base path is the directory of this script
            base_path = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the Sheet_Music folder
        self.SHEET_MUSIC_FOLDER = os.path.join(base_path, "Sheet_Music")
        # --- END OF FIX ---

        # --- Check if Sheet_Music folder exists ---
        if not os.path.exists(self.SHEET_MUSIC_FOLDER):
            messagebox.showerror(
                "错误",
                f"未找到 'Sheet_Music' 文件夹。\n请确保该文件夹存在于以下路径:\n{self.SHEET_MUSIC_FOLDER}"
            )
            self.root.destroy() # Close the app if folder is missing
            return
        # --- END OF CHECK ---

        self.create_widgets()
        self.populate_folder_list() # Populate the listbox on startup

    def create_widgets(self):
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Folder Selection (Listbox)
        folder_frame = ttk.LabelFrame(main_frame, text="选择曲谱文件夹", padding="10")
        folder_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        main_frame.columnconfigure(0, weight=1)

        self.folder_listbox = tk.Listbox(folder_frame, height=8)
        self.folder_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        folder_frame.columnconfigure(0, weight=1)
        folder_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(folder_frame, orient="vertical", command=self.folder_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.folder_listbox.configure(yscrollcommand=scrollbar.set)

        self.folder_listbox.bind('<<ListboxSelect>>', self.on_folder_select)

        # Manual Folder Selection Button
        self.select_folder_button = ttk.Button(folder_frame, text="手动选择文件夹...", command=self.browse_folder)
        self.select_folder_button.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)

        # Selected Folder Display
        selected_frame = ttk.Frame(main_frame)
        selected_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(selected_frame, text="当前选中:").grid(row=0, column=0, sticky=tk.W)
        self.selected_folder_label = ttk.Label(selected_frame, textvariable=self.folder_path, foreground="blue")
        self.selected_folder_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        # Play Mode Selection
        mode_frame = ttk.LabelFrame(main_frame, text="播放模式", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        self.scroll_radio = ttk.Radiobutton(mode_frame, text="滚动播放", variable=self.play_mode, value=ImageScroller.MODE_SCROLL)
        self.scroll_radio.grid(row=0, column=0, sticky=tk.W)

        self.tiled_radio = ttk.Radiobutton(mode_frame, text="平铺预览 (图片数<4)", variable=self.play_mode, value=ImageScroller.MODE_TILED)
        self.tiled_radio.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        # Initially disabled until folder is selected
        self.tiled_radio.config(state='disabled')

        # Speed Control
        speed_frame = ttk.LabelFrame(main_frame, text="播放速度", padding="10")
        speed_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(speed_frame, text="慢").grid(row=0, column=0, sticky=tk.W)
        self.speed_scale = ttk.Scale(speed_frame, from_=0.5, to=10.0, orient='horizontal', variable=self.speed)
        self.speed_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        speed_frame.columnconfigure(1, weight=1)
        ttk.Label(speed_frame, text="快").grid(row=0, column=2, sticky=tk.E)

        self.speed_label = ttk.Label(speed_frame, text=f"{self.speed.get():.1f}")
        self.speed_label.grid(row=1, column=1)
        self.speed_scale.configure(command=self.update_speed_label)

        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(0, 10))

        self.start_button = ttk.Button(button_frame, text="播放", command=self.start_playback)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))

        self.pause_button = ttk.Button(button_frame, text="暂停", command=self.pause_playback, state='disabled')
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))

        self.resume_button = ttk.Button(button_frame, text="继续", command=self.resume_playback, state='disabled')
        self.resume_button.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_playback, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        # Status Bar
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def populate_folder_list(self):
        """Populates the listbox with folders found in the Sheet_Music directory."""
        self.folder_listbox.delete(0, tk.END)
        try:
            items = os.listdir(self.SHEET_MUSIC_FOLDER)
            folders = [item for item in items if os.path.isdir(os.path.join(self.SHEET_MUSIC_FOLDER, item))]
            for folder in sorted(folders):
                self.folder_listbox.insert(tk.END, folder)
        except OSError as e:
            messagebox.showerror("错误", f"无法读取 'Sheet_Music' 文件夹: {e}")
            self.status_var.set("错误: 无法读取曲谱文件夹")

    def on_folder_select(self, event):
        """Handles selection from the listbox."""
        selection = self.folder_listbox.curselection()
        if selection:
            folder_name = self.folder_listbox.get(selection[0])
            full_path = os.path.join(self.SHEET_MUSIC_FOLDER, folder_name)
            self.folder_path.set(full_path)
            self._check_and_update_mode_options(full_path)

    def browse_folder(self):
        """Opens a dialog to manually select a folder."""
        folder_selected = filedialog.askdirectory(
            initialdir=self.SHEET_MUSIC_FOLDER,
            title="请选择包含吉他谱图片的文件夹"
        )
        if folder_selected:
            self.folder_path.set(folder_selected)
            self._check_and_update_mode_options(folder_selected)

    def _check_and_update_mode_options(self, folder_path):
        """Checks number of images and enables/disables tiled mode option."""
        try:
            if not os.path.isdir(folder_path):
                raise FileNotFoundError

            image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            num_images = len(image_files)

            if num_images >= 4:
                # Disable tiled mode
                self.tiled_radio.config(state='disabled')
                # Force selection to scroll mode if tiled was selected
                if self.play_mode.get() == ImageScroller.MODE_TILED:
                    self.play_mode.set(ImageScroller.MODE_SCROLL)
                print(f"检测到 {num_images} 张图片，平铺模式不可用。")
            else:
                # Enable tiled mode
                self.tiled_radio.config(state='normal')
                print(f"检测到 {num_images} 张图片，平铺模式可用。")
        except Exception as e:
            print(f"检查文件夹图片数量时出错: {e}")
            self.tiled_radio.config(state='disabled')
            if self.play_mode.get() == ImageScroller.MODE_TILED:
                self.play_mode.set(ImageScroller.MODE_SCROLL)

    def update_speed_label(self, value):
        """Updates the speed label when the scale is moved."""
        self.speed_label.config(text=f"{float(value):.1f}")

    def start_playback(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("错误", "请选择一个有效的文件夹。")
            return

        # Check for images in the selected folder
        image_files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            messagebox.showerror("错误", f"所选文件夹 '{os.path.basename(folder)}' 中未找到图片文件 (支持 .png, .jpg, .jpeg)")
            return

        selected_mode = self.play_mode.get()
        if selected_mode == ImageScroller.MODE_TILED:
             # Double-check as a safeguard
             if len(image_files) >= 4:
                 messagebox.showwarning("警告", "图片数量 >= 4，无法使用平铺模式。已切换到滚动模式。")
                 self.play_mode.set(ImageScroller.MODE_SCROLL)
                 selected_mode = ImageScroller.MODE_SCROLL

        # Reset events for new playback
        self.stop_event.clear()
        self.pause_event.clear()
        self.is_paused = False
        self.is_stopping = True 
        
        # Update UI state
        self.start_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.pause_button.config(state='disabled')
        self.resume_button.config(state='disabled')
        self.status_var.set(f"正在播放: {os.path.basename(folder)} ({selected_mode})")
        self.root.update()


        def on_playback_finished():
            self.root.after(0, self._reset_ui_state)


        # Pass the selected mode to the player, including the callback
        self.player = ImageScroller(folder, self.speed.get(), selected_mode, self.stop_event, self.pause_event, on_finished_callback=on_playback_finished)
        
        if not self.player.load_images():
            messagebox.showerror("错误", "加载图片列表失败。")
            self._reset_ui_state()
            return

        # Update UI based on mode
        self.stop_button.config(state='normal')
        if selected_mode == ImageScroller.MODE_SCROLL:
            self.pause_button.config(state='normal')
            # Resume button remains disabled until paused
        else: # Tiled mode
            self.pause_button.config(state='disabled') # Pause not applicable
            self.resume_button.config(state='disabled')

        # Start playback in a new thread
        self.scroll_thread = threading.Thread(target=self.player.run)
        self.scroll_thread.daemon = True
        self.scroll_thread.start()

    def stop_playback(self):
        """Stops the playback."""
        self.is_stopping = True
        self.stop_event.set()
        if self.is_paused:
            self.pause_event.set() # Ensure thread wakes up if paused
        self.status_var.set("正在停止...")

        self.root.after(10000, self._reset_ui_state) 

        # UI will be reset by the thread or after a short delay
        # We don't join here to avoid blocking the UI thread
        # The player's run method should handle the stop_event gracefully

    def pause_playback(self):
        """Pauses the playback."""
        if self.pause_event:
            self.pause_event.set()
            self.is_paused = True
            self.status_var.set("已暂停")
            self.pause_button.config(state='disabled')
            self.resume_button.config(state='normal')

    def resume_playback(self):
        """Resumes the playback."""
        if self.pause_event and self.is_paused:
            self.pause_event.clear()
            self.is_paused = False
            folder = self.folder_path.get()
            mode = self.play_mode.get()
            self.status_var.set(f"正在播放: {os.path.basename(folder)} ({mode})")
            self.pause_button.config(state='normal')
            self.resume_button.config(state='disabled')

    def _reset_ui_state(self):
        """Resets the UI to its initial state after playback stops."""
        if not self.is_stopping and self.start_button['state'] != 'disabled':
            return
        self.is_stopping = False 

        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.pause_button.config(state='disabled')
        self.resume_button.config(state='disabled')
        self.status_var.set("就绪")
        self.is_paused = False




