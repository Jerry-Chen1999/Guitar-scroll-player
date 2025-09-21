# 吉他谱滚动播放器 (Guitar Scroll Player)

一个用 Python 和 OpenCV 编写的简单应用程序，用于在电脑上滚动播放吉他或者其他乐器乐谱，或将多张图片平铺预览。

## 重要
*   请务必将曲谱按照 0,1,2,..., 的数字排列进行重命名


## 功能

*   **滚动模式**: 将一个文件夹内的多张吉他谱图片垂直拼接，并以设定的速度向上滚动播放，模拟真实翻页效果。
*   **平铺预览模式**: 将图片水平拼接成一张长图，方便快速浏览整首曲子的结构。
*   图片自动按数字排序 (例如 1.png, 2.png, 10.png)。
*   可调节播放速度。
*   支持暂停、继续和停止播放。
*   图片格式支持: `.png`, `.jpg`, `.jpeg`。

## 安装与运行

### 1. 克隆或下载仓库

```bash
git clone https://github.com/YourGitHubUsername/guitar-scroll-player.git
cd guitar-scroll-player