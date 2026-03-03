# -*- coding:utf-8 -*-
"""
文档问答系统API服务启动脚本

使用方法：
1. 确保已安装所有依赖：pip install fastapi uvicorn requests websocket-client requests-toolbelt
2. 运行此脚本：python start_server.py
3. 访问 http://localhost:8000/docs 查看API文档
"""
import subprocess
import sys
import os

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'requests',
        'websocket-client',
        'requests-toolbelt'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """安装缺失的依赖"""
    if not packages:
        return
    
    print(f"正在安装缺失的依赖: {', '.join(packages)}")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *packages])
        print("依赖安装成功!")
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}")
        sys.exit(1)

def start_server():
    """启动FastAPI服务"""
    print("正在启动文档问答系统API服务...")
    print("服务地址: http://localhost:8000")
    print("API文档地址: http://localhost:8000/docs")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 使用uvicorn启动main.py中的app
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'main:app', 
            '--host', '0.0.0.0', 
            '--port', '8000', 
            '--reload'
        ])
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"服务启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("文档问答系统API服务启动器")
    print("=" * 50)
    
    # 检查并安装依赖
    missing = check_dependencies()
    if missing:
        print(f"检测到缺失的依赖: {', '.join(missing)}")
        response = input("是否自动安装这些依赖？(y/n): ")
        if response.lower() == 'y':
            install_dependencies(missing)
        else:
            print("请手动安装这些依赖后再启动服务")
            sys.exit(1)
    else:
        print("所有依赖已正确安装")
    
    # 启动服务
    start_server()