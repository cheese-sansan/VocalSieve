# -*- coding: utf-8 -*-
"""
gui_main.py
===========
图形界面的启动入口。

使用 PyWebview 挂载本地前端，并将 VocalSieveApi 注入页面。
"""

import os
import sys
import webview
from web_api import VocalSieveApi

def get_base_path():
    """获取开发环境或 PyInstaller 打包环境下的资源根路径。"""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def main():
    api = VocalSieveApi()

    base_path = get_base_path()
    html_path = os.path.join(base_path, 'ui', 'index.html')

    window = webview.create_window(
        title='VocalSieve - 音频筛选控制台',
        url=html_path,  
        js_api=api,
        width=1000,
        height=750,
        min_size=(1000, 750),
        background_color='#121212'
    )

    api.set_window(window)
    webview.start(debug=False)

if __name__ == '__main__':
    main()
