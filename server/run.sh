#!/bin/bash

# 安装依赖
pip install -r requirements.txt

# 设置 Python 路径
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 启动服务器
python app/main.py
