# player.py
import os
import re
import cv2
import numpy as np
from PIL import Image
import threading
import time


class ImageScroller:
    """
    Handles loading, concatenating images and the OpenCV playback (scrolling or tiling).
    """
    MODE_SCROLL = "scroll"
    MODE_TILED = "tiled"

    def __init__(self, image_folder_path, speed, mode, stop_event, pause_event, on_finished_callback=None):
        self.image_folder_path = image_folder_path
        self.speed = speed
        self.mode = mode
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.on_finished_callback = on_finished_callback

        # --- FIXED: Use folder path as window name ---
        # Note: If the path contains non-ASCII characters that cause issues,
        # you might need to fall back to a generic name or encode it differently.
        # For now, we attempt to use the path directly.
        self.window_name_scroll = f"滚动模式 - {self.image_folder_path}"
        self.window_name_tiled = f"平铺模式 - {self.image_folder_path}"
        # --- END OF FIX ---
        
        self.initial_width, self.initial_height = 800, 1000

        self.image_files_sorted = []
        self.combined_image = None
        self.tiled_image = None
        self.display_image = None
        self.img_height = 0
        self.img_width = 0

    def sort_numerically(self, data_list):
        """Sorts a list of strings numerically based on the number in the filename."""
        def numerical_sort_key(name):
            numbers = re.findall(r'\d+', name)
            return int(numbers[0]) if numbers else float('inf')
        return sorted(data_list, key=numerical_sort_key)

    def load_images(self):
        """Loads and sorts image filenames."""
        try:
            if not os.path.isdir(self.image_folder_path):
                 raise FileNotFoundError(f"路径无效: {self.image_folder_path}")

            image_files = [f for f in os.listdir(self.image_folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if not image_files:
                raise FileNotFoundError("所选文件夹中未找到图片文件 (支持 .png, .jpg, .jpeg)")

            self.image_files_sorted = self.sort_numerically(image_files)
            return True
        except Exception as e:
            print(f"加载图片列表时出错: {e}")
            return False

    def prepare_scroll_mode(self):
        """Prepares the combined image for scrolling mode."""
        try:
            if not self.image_files_sorted:
                raise ValueError("图片列表为空")

            pil_images = []
            max_width = 0
            total_height = 0

            for filename in self.image_files_sorted:
                img_path = os.path.join(self.image_folder_path, filename)
                try:
                    img = Image.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    pil_images.append(img)
                    max_width = max(max_width, img.width)
                    total_height += img.height
                except Exception as e:
                    print(f"警告: 无法加载图片 {filename}: {e}")
                    return False

            if not pil_images:
                 raise FileNotFoundError("所选文件夹中未找到有效的图片文件")

            combined_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))

            y_offset = 0
            for img in pil_images:
                x_offset = (max_width - img.width) // 2
                combined_img.paste(img, (x_offset, y_offset))
                y_offset += img.height

            self.combined_image = np.array(combined_img)
            self.combined_image = self.combined_image[:, :, ::-1].copy()
            self.img_height, self.img_width = self.combined_image.shape[:2]
            self.display_image = self.combined_image.copy()
            return True

        except Exception as e:
            print(f"准备滚动模式时出错: {e}")
            return False

    def prepare_tiled_mode(self):
        """Prepares the tiled image for preview mode."""
        try:
            if not self.image_files_sorted:
                raise ValueError("图片列表为空")

            pil_images = []
            max_height = 0
            total_width = 0

            for filename in self.image_files_sorted:
                img_path = os.path.join(self.image_folder_path, filename)
                try:
                    img = Image.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    pil_images.append(img)
                    max_height = max(max_height, img.height)
                    total_width += img.width
                except Exception as e:
                    print(f"警告: 无法加载图片 {filename} 用于平铺: {e}")

            if not pil_images:
                 raise FileNotFoundError("所选文件夹中未找到有效的图片文件用于平铺")

            tiled_img = Image.new('RGB', (total_width, max_height), (200, 200, 200))

            x_offset = 0
            for img in pil_images:
                tiled_img.paste(img, (x_offset, 0))
                x_offset += img.width

            self.tiled_image = np.array(tiled_img)
            self.tiled_image = self.tiled_image[:, :, ::-1].copy()
            return True

        except Exception as e:
            print(f"准备平铺模式时出错: {e}")
            return False


    def run(self):
        """Public method to start the playback based on the selected mode."""
        if self.mode == self.MODE_SCROLL:
            if self.prepare_scroll_mode():
                self._run_scroll_mode()
            else:
                print("无法启动滚动模式。")
        elif self.mode == self.MODE_TILED:
             if self.prepare_tiled_mode():
                 self._run_tiled_mode()
             else:
                 print("无法启动平铺模式。")
        else:
            print(f"未知的播放模式: {self.mode}")

        # --- 新增：在线程结束时调用回调 ---
        if self.on_finished_callback:
            try:
                # print("Calling on_finished_callback") #
                self.on_finished_callback()
            except Exception as e:
                print(f"Error in on_finished_callback: {e}")


    def _run_scroll_mode(self):
        """Handles the scrolling logic using OpenCV in a resizable window."""
        if self.combined_image is None:
            print("错误：在开始滚动前未加载图像。")
            return

        # --- Use the updated window name ---
        cv2.namedWindow(self.window_name_scroll, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name_scroll, self.initial_width, self.initial_height)
        # --- END ---

        current_pos = 0
        delay_ms = max(1, int(50 / self.speed))
        prev_win_w, prev_win_h = self.initial_width, self.initial_height

        while not self.stop_event.is_set():
            while self.pause_event.is_set() and not self.stop_event.is_set():
                self._show_current_frame_scroll(current_pos, prev_win_w, prev_win_h)
                if cv2.waitKey(100) == 27:
                    self.stop_event.set()
                try:
                    rect = cv2.getWindowImageRect(self.window_name_scroll) # Use updated name
                    prev_win_w, prev_win_h = rect[2], rect[3]
                except: pass

            if self.stop_event.is_set():
                break

            try:
                rect = cv2.getWindowImageRect(self.window_name_scroll) # Use updated name
                win_w, win_h = rect[2], rect[3]
            except:
                win_w, win_h = prev_win_w, prev_win_h

            if abs(win_w - prev_win_w) > 10 or abs(win_h - prev_win_h) > 10:
                scale_w = win_w / self.img_width
                new_width = max(1, int(self.img_width * scale_w))
                new_height = max(1, int(self.img_height * scale_w))
                
                if new_width != self.display_image.shape[1] or new_height != self.display_image.shape[0]:
                     self.display_image = cv2.resize(self.combined_image, (new_width, new_height))
                
                prev_win_w, prev_win_h = win_w, win_h

            disp_img_h = self.display_image.shape[0]

            if current_pos + win_h >= disp_img_h:
                print("已滚动到末尾（底部对齐），暂停2分钟...")
                pause_start_time = time.time()
                while time.time() - pause_start_time < 120 and not self.stop_event.is_set():
                     self._show_current_frame_scroll(current_pos, win_w, win_h)
                     if cv2.waitKey(500) == 27:
                         self.stop_event.set()
                         break
                
                if not self.stop_event.is_set():
                    current_pos = 0
                    print("重新开始滚动...")
                continue

            self._show_current_frame_scroll(current_pos, win_w, win_h)
            key = cv2.waitKey(delay_ms) & 0xFF
            if key == 27:
                self.stop_event.set()
                break

            current_pos += int(max(1, self.speed))


        try:
            cv2.destroyWindow(self.window_name_scroll) # Use updated name
        except: pass

    def _show_current_frame_scroll(self, current_pos, win_w, win_h):
        """Helper to display the current visible portion for scroll mode."""
        current_pos = int(current_pos)
        disp_img_h = self.display_image.shape[0]
        end_pos = min(current_pos + win_h, disp_img_h)
        visible_img = self.display_image[current_pos:end_pos, :]

        if visible_img.shape[0] < win_h:
             pad_bottom = win_h - visible_img.shape[0]
             visible_img = cv2.copyMakeBorder(visible_img, 0, pad_bottom, 0, 0, cv2.BORDER_CONSTANT, value=(255,255,255))
        if visible_img.shape[1] < win_w:
             pad_right = win_w - visible_img.shape[1]
             visible_img = cv2.copyMakeBorder(visible_img, 0, 0, 0, pad_right, cv2.BORDER_CONSTANT, value=(255,255,255))

        cv2.imshow(self.window_name_scroll, visible_img) # Use updated name


    def _run_tiled_mode(self):
        """Handles the tiled preview logic using OpenCV."""
        if self.tiled_image is None:
            print("错误：在开始平铺预览前未加载图像。")
            return

        # --- Use the updated window name ---
        cv2.namedWindow(self.window_name_tiled, cv2.WINDOW_NORMAL)
        # --- END ---
        h, w = self.tiled_image.shape[:2]
        cv2.resizeWindow(self.window_name_tiled, min(w, 1200), min(h, 800))

        try:
            rect = cv2.getWindowImageRect(self.window_name_tiled) # Use updated name
            win_w, win_h = rect[2], rect[3]
        except:
             win_w, win_h = 800, 600

        self.display_image = self._resize_tiled_image_to_window(win_w, win_h)
        prev_win_w, prev_win_h = win_w, win_h

        view_x, view_y = 0, 0
        if self.display_image.shape[1] > win_w:
            view_x = (self.display_image.shape[1] - win_w) // 2
        if self.display_image.shape[0] > win_h:
            view_y = (self.display_image.shape[0] - win_h) // 2

        is_dragging = False
        last_x, last_y = 0, 0

        def onMouse(event, x, y, flags, param):
            nonlocal is_dragging, last_x, last_y, view_x, view_y
            if event == cv2.EVENT_LBUTTONDOWN:
                is_dragging = True
                last_x, last_y = x, y
            elif event == cv2.EVENT_MOUSEMOVE and is_dragging:
                dx, dy = x - last_x, y - last_y
                view_x = max(0, min(view_x - dx, self.display_image.shape[1] - win_w))
                view_y = max(0, min(view_y - dy, self.display_image.shape[0] - win_h))
                last_x, last_y = x, y
            elif event == cv2.EVENT_LBUTTONUP:
                is_dragging = False

        cv2.setMouseCallback(self.window_name_tiled, onMouse) # Use updated name

        print("平铺模式: 按 'ESC' 键退出。")

        while not self.stop_event.is_set():
             try:
                 rect = cv2.getWindowImageRect(self.window_name_tiled) # Use updated name
                 win_w, win_h = rect[2], rect[3]
             except:
                 win_w, win_h = prev_win_w, prev_win_h

             if abs(win_w - prev_win_w) > 10 or abs(win_h - prev_win_h) > 10:
                  self.display_image = self._resize_tiled_image_to_window(win_w, win_h)
                  view_x = max(0, min(view_x, self.display_image.shape[1] - win_w))
                  view_y = max(0, min(view_y, self.display_image.shape[0] - win_h))
                  prev_win_w, prev_win_h = win_w, win_h

             view_x = max(0, min(view_x, self.display_image.shape[1] - win_w))
             view_y = max(0, min(view_y, self.display_image.shape[0] - win_h))

             visible_img = self.display_image[view_y:view_y+win_h, view_x:view_x+win_w]
             if visible_img.shape[0] < win_h or visible_img.shape[1] < win_w:
                  visible_img = cv2.copyMakeBorder(visible_img, 0, win_h - visible_img.shape[0],
                                                   0, win_w - visible_img.shape[1],
                                                   cv2.BORDER_CONSTANT, value=(200, 200, 200))

             cv2.imshow(self.window_name_tiled, visible_img) # Use updated name

             key = cv2.waitKey(30) & 0xFF
             if key == 27:
                 self.stop_event.set()
                 break

        try:
            cv2.destroyWindow(self.window_name_tiled) # Use updated name
        except: pass
        cv2.destroyAllWindows()


        if self.on_finished_callback:
            try:
                self.on_finished_callback()
            except Exception as e:
                print(f"Error in on_finished_callback for tiled mode: {e}")



    def _resize_tiled_image_to_window(self, win_w, win_h):
        """Resizes the tiled image to fit within the window while maintaining aspect ratio."""
        img_h, img_w = self.tiled_image.shape[:2]
        scale_w = win_w / img_w
        scale_h = win_h / img_h
        scale = min(scale_w, scale_h, 1.0)

        if scale < 1.0:
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            return cv2.resize(self.tiled_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            return self.tiled_image.copy()




