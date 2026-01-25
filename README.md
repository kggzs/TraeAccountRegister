# Trae 账号注册工具

一个基于 Playwright + 临时邮箱的自动化注册脚本，支持单账号注册与批量并发注册，并在完成后导出账号信息、Cookie 和 Token。

---

## ⭐ Star 星星走起 动动发财手点点 ⭐

> 如果这个项目对你有帮助，请不要吝啬你的 Star ⭐
> 你的支持是我持续更新的最大动力！💪

<div align="center">

### 👆 点击右上角 Star 按钮支持一下吧！ 👆

</div>

---

## ✨ 功能特性

### 核心功能
- 🔐 **自动注册流程**：自动生成临时邮箱、获取验证码、完成注册
- 🎁 **自动领取礼包**：注册成功后自动领取周年礼包
- 💾 **数据导出**：自动保存账号信息、浏览器 Cookie 和 GetUserToken
- ⚡ **批量并发**：支持批量注册，可自定义总数量和并发数
- 🌐 **Web 界面**：提供现代化的 Web 管理界面，实时查看进度和日志
- 🔑 **Token 管理**：支持为已注册账号获取和导出 Token
- 📁 **文件管理**：Web 界面查看和管理所有导出的文件

### 使用模式
- **CLI 模式**：命令行直接运行，适合脚本自动化
- **Web 模式**：通过浏览器访问，提供可视化操作界面

## 🔗 相关项目推荐

### Trae 账户管理器

注册完账号后，建议配合使用 **[Trae 账户管理器](https://github.com/Yang-505/Trae-Account-Manager)** 来管理多个 Trae 账号。

**Trae 账户管理器** 是一款专为 Trae IDE 用户打造的多账号高效管理工具，提供以下功能：

- 🔄 **一键切换账号**：快速切换不同的 Trae 账号
- 📊 **实时使用量监控**：查看每个账号的使用情况
- 📝 **使用记录查询**：查看详细的使用历史
- 💾 **数据导入导出**：方便备份和迁移账号数据
- ⚙️ **机器码管理**：管理 Trae IDE 的机器码绑定

**使用流程**：
1. 使用本工具批量注册 Trae 账号
2. 使用 Trae 账户管理器导入注册的账号
3. 在 Trae 账户管理器中一键切换账号，充分利用每个账号的额度

> 💡 **提示**：两个工具配合使用，可以更高效地管理和使用多个 Trae 账号！

## 📋 目录结构

```
TraeAccountRegister/
├── register.py          # 主入口脚本（包含注册逻辑和 Web API）
├── mail_client.py       # 临时邮箱客户端
├── token_manager.py     # Token 管理器（GUI 版本，可选）
├── requirements.txt     # Python 依赖列表
├── static/
│   └── index.html       # Web 界面
├── cookies/             # Cookie 导出目录（运行时自动创建）
├── GetUserToken/        # Token 导出目录（运行时自动创建）
└── accounts.txt         # 账号列表文件（追加写入）
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows / Linux / macOS

### 安装步骤

1. **克隆或下载项目**
```bash
cd TraeAccountRegister
```

2. **创建虚拟环境（推荐）**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **安装 Playwright 浏览器**
```bash
python -m playwright install chromium
```

## 📖 使用方法

### 方式一：Web 界面（推荐）

1. **启动服务**
```bash
python register.py
```

2. **访问 Web 界面**
   - 打开浏览器访问：`http://localhost:8001`
   - 默认端口为 8001，可通过环境变量 `PORT` 修改

3. **功能说明**
   - **账号注册标签页**：设置注册数量和并发数，开始批量注册
   - **Token 管理标签页**：为已注册账号获取 Token
   - **文件管理标签页**：查看和管理导出的账号、Cookie、Token 文件

### 方式二：命令行模式

1. **单账号注册**
```bash
python register.py
```

2. **批量注册**
```bash
python register.py [总数量] [并发数]
```

**参数说明**：
- `总数量`：要注册的账号总数（必填）
- `并发数`：同时运行的注册任务数（可选，默认为 1）

**示例**：
```bash
# 注册 10 个账号，并发数为 3
python register.py 10 3

# 注册 1 个账号（单账号模式）
python register.py 1 1
```

### 方式三：Token 管理器（GUI）

如果需要单独使用 Token 管理器 GUI 工具：

```bash
python token_manager.py
```

## 📊 输出文件说明

### accounts.txt
账号列表文件，格式：
```
Email    Password
example@uuf.me    Abc123!@#
```

### cookies/
每个账号的 Cookie JSON 文件，文件名格式：`邮箱.json`

### GetUserToken/
每个账号的 GetUserToken JSON 文件，文件名格式：`邮箱.json`

## 🔧 API 接口（Web 模式）

### WebSocket 连接
- **路径**：`/ws`
- **功能**：实时接收日志、统计信息和状态更新

### REST API

#### 启动注册
- **路径**：`POST /api/start`
- **参数**：
  - `total`：注册总数（必填）
  - `concurrency`：并发数（必填）

#### 停止注册
- **路径**：`POST /api/stop`
- **功能**：停止当前正在运行的注册任务

#### 获取统计信息
- **路径**：`GET /api/stats`
- **返回**：`{success, fail, total, pending}`

#### 获取账号列表
- **路径**：`GET /api/accounts`
- **返回**：账号列表数组

#### 获取 Token
- **路径**：`POST /api/get-token`
- **参数**：
  - `email`：邮箱地址（必填）
  - `password`：密码（必填）

#### 文件管理 API
- `GET /api/file/accounts` - 获取 accounts.txt 内容
- `GET /api/file/cookies` - 列出所有 Cookie 文件
- `GET /api/file/cookies/{filename}` - 获取指定 Cookie 文件内容
- `GET /api/file/tokens` - 列出所有 Token 文件
- `GET /api/file/tokens/{filename}` - 获取指定 Token 文件内容

## ⚙️ 配置说明

### 临时邮箱配置
在 `mail_client.py` 中可以修改：
- `API_BASE_URL`：临时邮箱 API 地址
- `KNOWN_DOMAINS`：可用的邮箱域名列表

### 浏览器配置
在 `register.py` 中可以修改：
- `headless`：是否无头模式（默认 `True`）
- 浏览器启动参数

## ⚠️ 注意事项

1. **并发数建议**：
   - 建议并发数设置为 3-5
   - 并发数过高可能导致：
     - 资源占用过大
     - 失败率上升
     - 临时邮箱 API 限流

2. **网络环境**：
   - 确保网络连接稳定
   - 某些地区可能需要代理

3. **验证码接收**：
   - 验证码接收有 60 秒超时限制
   - 如果超时未收到，任务会标记为失败

4. **文件管理**：
   - 所有文件都是追加写入，不会覆盖已有数据
   - 建议定期备份 `accounts.txt` 和 `cookies/` 目录

5. **浏览器资源**：
   - 每个并发任务会启动一个浏览器实例
   - 确保系统有足够的内存和 CPU 资源

## 🛠️ 故障排除

### 问题：Playwright 浏览器安装失败
**解决方案**：
```bash
# 手动安装 Chromium
python -m playwright install chromium

# 如果网络问题，可以设置代理
set HTTP_PROXY=http://proxy:port
set HTTPS_PROXY=http://proxy:port
python -m playwright install chromium
```

### 问题：验证码接收超时
**可能原因**：
- 临时邮箱服务不稳定
- 网络延迟
- 邮件发送延迟

**解决方案**：
- 降低并发数
- 检查网络连接
- 等待一段时间后重试

### 问题：注册失败率较高
**可能原因**：
- 并发数过高
- 目标网站检测到自动化行为
- 临时邮箱被限制

**解决方案**：
- 降低并发数到 1-2
- 增加操作之间的延迟
- 更换临时邮箱服务

### 问题：Web 界面无法访问
**检查项**：
- 确认服务已启动（查看终端输出）
- 检查端口是否被占用
- 尝试使用 `http://127.0.0.1:8001` 访问
- 检查防火墙设置

## 📦 依赖说明

主要依赖包：
- `playwright`：浏览器自动化
- `httpx`：HTTP 客户端（临时邮箱 API）
- `fastapi`：Web 框架
- `uvicorn`：ASGI 服务器
- `python-multipart`：表单数据处理

完整依赖列表请查看 `requirements.txt`。

## 🔒 免责声明

<div align="center">

### 📢 重要提示：请仔细阅读以下声明

</div>

> **本工具仅供学习和技术研究使用，使用前请务必了解以下内容：**

- ⚠️ **风险自负**：使用者需自行承担所有风险，包括但不限于系统损坏、数据丢失、账号异常等
- ⚖️ **法律风险**：本工具可能违反软件使用协议，请自行评估法律风险
- 🚫 **责任豁免**：作者不承担任何直接或间接损失责任
- 📚 **使用限制**：仅限个人学习研究，严禁商业用途
- 🔒 **授权声明**：不得用于绕过软件正当授权机制
- ✅ **同意条款**：继续使用即表示您已理解并同意承担相应风险

<div align="center">

**⚠️ 如果您不同意以上条款，请立即停止使用本工具 ⚠️**

</div>

## 📝 更新日志

### v1.0.0
- ✅ 基础注册功能
- ✅ 批量并发注册
- ✅ Web 界面管理
- ✅ Token 获取功能
- ✅ 文件管理功能
- ✅ Cookie 导出功能

## 🙏 项目来源

本项目基于 [S-Trespassing/Trae-Account-Creator](https://github.com/S-Trespassing/Trae-Account-Creator) 魔改而来。

感谢原项目作者的开源贡献！本项目在原有基础上进行了以下改进和扩展：

- ✨ 添加了 Web 界面管理功能
- 🔑 集成了 Token 获取和管理功能
- 📁 增加了文件管理功能
- 🎨 优化了用户体验和界面设计

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目仅供学习研究使用。

---

**注意**：使用本工具时请遵守相关法律法规和网站服务条款。
