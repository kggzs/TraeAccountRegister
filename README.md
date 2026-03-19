# Trae 账号注册工具(已停止更新)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Playwright](https://img.shields.io/badge/Playwright-Automated-green)
![FastAPI](https://img.shields.io/badge/FastAPI-Web%20UI-teal)

**一个基于 Playwright + 临时邮箱的自动化注册脚本**

[功能特性](#-功能特性) • [目录结构](#-目录结构) • [快速开始](#-快速开始) • [使用指南](#-使用指南) • [相关项目](#-相关项目推荐)

</div>

---

## 📖 简介

Trae 账号注册工具是一个强大的自动化工具，旨在简化 Trae 账号的注册流程。它集成了临时邮箱服务，支持单账号注册与批量并发注册。除了基本的注册功能外，它还能自动领取周年礼包，并导出账号信息、浏览器 Cookie 和 GetUserToken，方便后续使用。

提供 **CLI（命令行）** 和 **Web（网页界面）** 两种使用模式，满足不同用户的需求。

## ✨ 功能特性

### 核心能力
- 🔐 **全自动注册**：自动生成临时邮箱、接收验证码、完成注册流程。
- 🎁 **自动领奖**：注册成功后自动领取周年礼包。
- 💾 **数据导出**：
    - 账号密码保存至 `accounts.txt`
    - 浏览器 Cookie 保存至 `cookies/` 目录
    - User Token 保存至 `GetUserToken/` 目录
- ⚡ **批量并发**：支持自定义注册数量和并发数，高效批量作业。
- 🌐 **Web 管理界面**：
    - 实时日志显示
    - 进度监控
    - 文件查看与下载
    - Token 独立获取功能

## 📋 目录结构

```text
TraeAccountRegister/
├── register.py          # 核心程序（包含 CLI 逻辑和 Web Server）
├── mail_client.py       # 临时邮箱客户端实现
├── token_manager.py     # Token 管理器（GUI 工具）
├── requirements.txt     # 项目依赖文件
├── accounts.txt         # 注册成功的账号列表（自动生成）
├── static/              # Web 界面静态资源
│   └── index.html
├── cookies/             # 存放导出的 Cookie 文件（自动生成）
└── GetUserToken/        # 存放导出的 Token 文件（自动生成）
```

## 🚀 快速开始

### 环境要求
- **操作系统**: Windows / Linux / macOS
- **Python**: 3.8 或更高版本

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd TraeAccountRegister
   ```

2. **创建虚拟环境 (推荐)**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **安装 Playwright 浏览器**
   ```bash
   playwright install chromium
   ```

## � 使用指南

### 🌐 Web 模式 (推荐)

提供可视化的操作界面，适合大多数用户。

1. **启动服务**
   ```bash
   python register.py
   ```
2. **访问界面**
   打开浏览器访问: `http://localhost:8001`
3. **操作说明**
   - 在界面输入想要注册的总数量和并发数。
   - 点击“开始注册”按钮。
   - 实时查看右侧日志和下方进度条。
   - 完成后可在“文件管理”标签页下载账号列表或 Token 文件。

### 💻 CLI 模式 (命令行)

适合需要集成到脚本或在无头服务器运行的场景。

```bash
# 语法: python register.py [总数量] [并发数]

# 示例: 注册 1 个账号
python register.py 1

# 示例: 并发注册 5 个账号
python register.py 5 2
```

### 🛠️ Token 管理器 (GUI)

一个独立的桌面应用程序，用于便捷地管理账号和提取 Token/Cookies。

1. **启动工具**
   ```bash
   python token_manager.py
   ```

2. **核心功能**
   - **可视化管理**：自动加载 `accounts.txt` 中的账号列表，左侧列表点击即可查看详情。
   - **一键提取**：
     - 选中账号后点击“获取 Token & Cookies”按钮。
     - 程序会自动启动无头浏览器，模拟登录并提取凭证。
     - **极速模式**：内置性能优化，自动拦截图片/媒体资源加载，提升提取速度。
   - **数据展示与导出**：
     - 提取成功后，Token 和 Cookies 会直接显示在界面文本框中。
     - 支持“复制 Token”和“复制 Cookies”一键复制到剪贴板。
     - 自动保存文件：
       - Token 保存至 `GetUserToken/<email>.json`
       - Cookies 保存至 `cookies/<email>.json`
   - **实时日志**：界面右下角显示详细的操作日志，方便监控运行状态和排查错误。

## � 相关项目推荐

### [Trae 账户管理器](https://github.com/Yang-505/Trae-Account-Manager)

注册完账号后，建议配合使用 **[Trae 账户管理器](https://github.com/Yang-505/Trae-Account-Manager)** 来管理多个 Trae 账号。

**Trae 账户管理器** 是一款专为 Trae IDE 用户打造的多账号高效管理工具，提供以下功能：

- 🔄 **一键切换账号**：快速切换不同的 Trae 账号
- 📊 **实时使用量监控**：查看每个账号的使用情况
- 📝 **使用记录查询**：查看详细的使用历史
- 💾 **数据导入导出**：方便备份和迁移账号数据
- ⚙️ **机器码管理**：管理 Trae IDE 的机器码绑定

> 💡 **最佳实践**：使用本工具批量注册 -> 导入到 Trae 账户管理器 -> 高效切换使用。

## 🙏 项目来源

本项目基于 [Trae-Account-Creator](https://github.com/S-Trespassing/Trae-Account-Creator) 魔改而来。

感谢原项目作者的开源贡献！本项目在原有基础上进行了以下改进和扩展：

- ✨ 添加了 Web 界面管理功能
- 🔑 集成了 Token 获取和管理功能
- 📁 增加了文件管理功能
- 🎨 优化了用户体验和界面设计

## ⚠️ 免责声明

本工具仅供学习和研究使用。请勿用于任何非法用途或违反 Trae 服务条款的行为。开发者不对因使用本工具而产生的任何后果负责。

## ⭐ 支持项目

如果这个项目对你有帮助，请给一个 Star ⭐！

<div align="center">
  <b>你的支持是我持续更新的最大动力！💪</b>
</div>
