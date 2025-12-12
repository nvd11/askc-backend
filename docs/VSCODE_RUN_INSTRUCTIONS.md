# VSCode 运行说明

## 问题描述
在 VSCode 中直接运行 `src/main.py` 或 `test.py` 时会出现 `ModuleNotFoundError: No module named 'src'` 错误。

## 解决方案
已通过以下配置修复此问题：

1. **`.env` 文件**：
   ```env
   PYTHONPATH=/home/gateman/projects/github/langchain-mcp
   ```

2. **`.vscode/settings.json`**：
   - 添加了 `terminal.integrated.env.linux` 设置
   - 确保终端环境变量正确设置

3. **`.vscode/launch.json`**：
   - 设置了 `PYTHONPATH` 环境变量
   - 设置了正确的工作目录 `cwd`

## 重要步骤
**需要重启 VSCode 窗口来应用配置更改：**
1. 按 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (Mac)
2. 输入 "Developer: Reload Window"
3. 按回车重新加载 VSCode

## 验证方法
重新加载 VSCode 后，您可以在 VSCode 中：
1. 打开 `src/main.py` 或 `test.py`
2. 点击 VSCode 的运行按钮（或按 F5）
3. 程序应该能正常运行

## 手动测试命令
```bash
# 运行 main.py
PYTHONPATH=/home/gateman/projects/github/langchain-mcp python src/main.py

# 运行 test.py  
PYTHONPATH=/home/gateman/projects/github/langchain-mcp python test.py
```

## 配置验证
