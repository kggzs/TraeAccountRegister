import asyncio
import random
import string
import os
import re
import json
import sys
from playwright.async_api import async_playwright
from mail_client import AsyncMailClient
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import uvicorn

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
GET_USER_TOKEN_DIR = os.path.join(BASE_DIR, "GetUserToken")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(GET_USER_TOKEN_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# FastAPI app
app = FastAPI(title="Trae 账号生成器 & Token 管理器")

# Global state
class AppState:
    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self.stats = {'success': 0, 'fail': 0, 'total': 0, 'pending': 0}
        self.websockets = set()
        self.token_is_running = False
        self.current_token = ""
    
    def log(self, message: str):
        """Broadcast log message to all connected websockets"""
        for ws in self.websockets.copy():
            try:
                asyncio.create_task(ws.send_json({"type": "log", "message": message}))
            except:
                self.websockets.discard(ws)
    
    def update_stats(self):
        """Broadcast stats update to all connected websockets"""
        for ws in self.websockets.copy():
            try:
                asyncio.create_task(ws.send_json({"type": "stats", "stats": self.stats}))
            except:
                self.websockets.discard(ws)

app_state = AppState()

# --- Core Logic ---

def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

async def save_account(email, password):
    write_header = not os.path.exists(ACCOUNTS_FILE) or os.path.getsize(ACCOUNTS_FILE) == 0
    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
        if write_header:
            f.write("Email    Password\n")
        f.write(f"{email}    {password}\n")
    app_state.log(f"账号已保存到: {ACCOUNTS_FILE}")

async def run_registration():
    """
    Returns True if success, False if failed
    """
    app_state.log("开始单账号注册流程...")
    
    mail_client = AsyncMailClient()
    browser = None
    context = None
    page = None

    try:
        # 1. Setup Mail
        await mail_client.start()
        email = mail_client.get_email()
        password = generate_password()

        # 2. Setup Browser
        async with async_playwright() as p:
            app_state.log("启动浏览器...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
        
            # 3. Sign Up Process
            app_state.log("打开注册页面...")
            await page.goto("https://www.trae.ai/sign-up")
            
            await page.get_by_role("textbox", name="Email").fill(email)
            await page.get_by_text("Send Code").click()
            app_state.log("验证码已发送，等待邮件...")

            verification_code = None
            for i in range(12): 
                if app_state.should_stop: 
                    raise Exception("用户停止")
                await mail_client.check_emails()
                if mail_client.last_verification_code:
                    verification_code = mail_client.last_verification_code
                    break
                app_state.log(f"正在检查邮箱... ({i+1}/12)")
                await asyncio.sleep(5)

            if not verification_code:
                app_state.log("60秒内未收到验证码。")
                return False

            await page.get_by_role("textbox", name="Verification code").fill(verification_code)
            await page.get_by_role("textbox", name="Password").fill(password)

            signup_btns = page.get_by_text("Sign Up")
            if await signup_btns.count() > 1:
                await signup_btns.nth(1).click()
            else:
                await signup_btns.click()
            
            app_state.log("正在提交注册...")

            try:
                await page.wait_for_url(lambda url: "/sign-up" not in url, timeout=20000)
                app_state.log("注册成功（页面已跳转）")
            except:
                if await page.locator(".error-message").count() > 0:
                    err = await page.locator(".error-message").first.inner_text()
                    app_state.log(f"注册失败：{err}")
                    return False
                app_state.log("注册成功检查超时，继续后续流程...")

            await save_account(email, password)

            # 4. Claim Gift
            app_state.log("检查周年礼包...")
            try:
                await page.goto("https://www.trae.ai/2026-anniversary-gift")
                await page.wait_for_load_state("networkidle")
                claim_btn = page.get_by_role("button", name=re.compile("claim", re.IGNORECASE))
                if await claim_btn.count() > 0:
                    text = await claim_btn.first.inner_text()
                    if "claimed" not in text.lower():
                        await claim_btn.first.click()
                        app_state.log("礼包领取成功！")
            except Exception as e:
                app_state.log(f"礼包领取非关键错误: {e}")

            # 5. Get User Token
            app_state.log("正在获取 GetUserToken...")
            try:
                async with page.expect_response(lambda response: "GetUserToken" in response.url and response.status == 200, timeout=10000) as response_info:
                    await page.goto("https://www.trae.ai/account-setting#account")
                
                response = await response_info.value
                token_data = await response.json()
                token_path = os.path.join(GET_USER_TOKEN_DIR, f"{email}.json")
                with open(token_path, "w", encoding="utf-8") as f:
                    json.dump(token_data, f, ensure_ascii=False, indent=2)
                app_state.log(f"GetUserToken 已保存")
            except Exception:
                app_state.log("获取 GetUserToken 失败或超时 (非致命)")

            # 6. Save Cookies
            cookies = await context.cookies()
            cookie_path = os.path.join(COOKIES_DIR, f"{email}.json")
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f)
            app_state.log(f"Cookies 已保存")

            return True

    except Exception as e:
        app_state.log(f"流程异常：{e}")
        return False
    finally:
        if mail_client:
            await mail_client.close()

async def run_batch(total, concurrency):
    if total <= 0 or concurrency <= 0: 
                return
    concurrency = min(concurrency, total)
    app_state.log(f"开始批量注册，目标：{total}，并发：{concurrency}")

    queue = asyncio.Queue()
    for i in range(1, total + 1):
        queue.put_nowait(i)
    for _ in range(concurrency):
        queue.put_nowait(None)

    async def worker(worker_id):
        while True:
            if app_state.should_stop:
                app_state.log(f"[线程 {worker_id}] 检测到停止信号，退出。")
                queue.task_done()
                return
        
            index = await queue.get()
            if index is None:
                queue.task_done()
                return
            
            # Update stats: Pending + 1
            app_state.stats['pending'] += 1
            app_state.update_stats()

            app_state.log(f"[线程 {worker_id}] 处理任务 {index}/{total}...")
            try:
                success = await run_registration()
                if success:
                    app_state.stats['success'] += 1
                else:
                    app_state.stats['fail'] += 1
            except Exception:
                app_state.stats['fail'] += 1
            finally:
                app_state.stats['pending'] -= 1
                app_state.update_stats()
                app_state.log(f"[线程 {worker_id}] 任务 {index} 结束。")
                queue.task_done()

    tasks = [asyncio.create_task(worker(i + 1)) for i in range(concurrency)]
    await queue.join()
    
    # Cancel tasks if stopped
    if app_state.should_stop:
        for t in tasks: 
            t.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    app_state.is_running = False
    app_state.log(">>> 任务结束 <<<")

# --- API Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>请创建 static/index.html 文件</h1>"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    app_state.websockets.add(websocket)
    try:
        # Send initial stats
        await websocket.send_json({"type": "stats", "stats": app_state.stats})
        await websocket.send_json({"type": "status", "is_running": app_state.is_running})
        
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        app_state.websockets.discard(websocket)

@app.post("/api/start")
async def start_registration(total: int = Form(...), concurrency: int = Form(...)):
    """Start registration process"""
    if app_state.is_running:
        return {"success": False, "message": "任务已在运行中"}
    
    if total <= 0 or concurrency <= 0:
        return {"success": False, "message": "参数无效"}
    
    app_state.is_running = True
    app_state.should_stop = False
    app_state.stats = {'success': 0, 'fail': 0, 'total': total, 'pending': 0}
    app_state.update_stats()

    # Start batch in background
    asyncio.create_task(run_batch(total, concurrency))
    
    return {"success": True, "message": "任务已启动"}

@app.post("/api/stop")
async def stop_registration():
    """Stop registration process"""
    if app_state.is_running:
        app_state.should_stop = True
        app_state.log(">>> 正在停止任务... (等待当前操作完成) <<<")
        return {"success": True, "message": "停止信号已发送"}
    return {"success": False, "message": "没有运行中的任务"}

@app.get("/api/stats")
async def get_stats():
    """Get current statistics"""
    return app_state.stats

@app.get("/api/accounts")
async def get_accounts():
    """Get list of accounts"""
    accounts = []
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Skip header
            start_idx = 0
            if lines and "Email" in lines[0] and "Password" in lines[0]:
                start_idx = 1
            for line in lines[start_idx:]:
                parts = line.strip().split()
                if len(parts) >= 2:
                    accounts.append({"email": parts[0], "password": parts[1]})
        except Exception as e:
            return {"success": False, "error": str(e), "accounts": []}
    return {"success": True, "accounts": accounts}

@app.post("/api/get-token")
async def get_token(email: str = Form(...), password: str = Form(...)):
    """Get token for an account"""
    if app_state.token_is_running:
        return {"success": False, "message": "Token获取任务已在运行中"}
    
    app_state.token_is_running = True
    app_state.current_token = ""
    
    async def token_task():
        try:
            await get_token_logic(email, password)
        finally:
            app_state.token_is_running = False
    
    asyncio.create_task(token_task())
    return {"success": True, "message": "Token获取任务已启动"}

@app.get("/api/file/accounts")
async def get_accounts_file():
    """Get accounts.txt content"""
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content}
        else:
            return {"success": False, "error": "文件不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/file/cookies")
async def list_cookies_files():
    """List all cookie files"""
    try:
        files = []
        if os.path.exists(COOKIES_DIR):
            for f in os.listdir(COOKIES_DIR):
                if f.endswith('.json'):
                    files.append(f)
        return {"success": True, "files": sorted(files)}
    except Exception as e:
        return {"success": False, "error": str(e), "files": []}

@app.get("/api/file/cookies/{filename}")
async def get_cookie_file(filename: str):
    """Get specific cookie file content"""
    try:
        file_path = os.path.join(COOKIES_DIR, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content}
        else:
            return {"success": False, "error": "文件不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/file/tokens")
async def list_token_files():
    """List all token files"""
    try:
        files = []
        if os.path.exists(GET_USER_TOKEN_DIR):
            for f in os.listdir(GET_USER_TOKEN_DIR):
                if f.endswith('.json'):
                    files.append(f)
        return {"success": True, "files": sorted(files)}
    except Exception as e:
        return {"success": False, "error": str(e), "files": []}

@app.get("/api/file/tokens/{filename}")
async def get_token_file(filename: str):
    """Get specific token file content"""
    try:
        file_path = os.path.join(GET_USER_TOKEN_DIR, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content}
        else:
            return {"success": False, "error": "文件不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_token_logic(email, password):
    """Get token logic"""
    app_state.log(f"正在启动浏览器获取 {email} 的 Token...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, 
                                            args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        try:
            app_state.log("正在打开登录页面...")
            await page.goto("https://www.trae.ai/login")
            
            app_state.log("正在输入账号密码...")
            try:
                await page.wait_for_selector('input[type="email"]', timeout=10000)
                await page.fill('input[type="email"]', email)
            except:
                await page.get_by_role("textbox", name="Email").fill(email)

            try:
                if not await page.locator('input[type="password"]').is_visible():
                    app_state.log("检查是否需要点击继续...")
                    btns = page.locator('button')
                    count = await btns.count()
                    for i in range(count):
                        txt = await btns.nth(i).inner_text()
                        if "continue" in txt.lower() or "next" in txt.lower():
                            await btns.nth(i).click()
                            break
                
                await page.wait_for_selector('input[type="password"]', timeout=5000)
                await page.fill('input[type="password"]', password)
            except Exception as e:
                app_state.log(f"密码输入框查找失败: {e}")
                await page.get_by_role("textbox", name="Password").fill(password)

            app_state.log("提交登录...")
            try:
                if await page.locator('.btn-submit').is_visible():
                    app_state.log("检测到 .btn-submit 按钮，点击...")
                    await page.locator('.btn-submit').click()
                elif await page.locator('button[type="submit"]').is_visible():
                    await page.click('button[type="submit"]')
                else:
                    raise Exception("未找到常规提交按钮")
            except Exception as e:
                app_state.log(f"常规点击失败 ({e})，尝试文本匹配...")
                clicked = False
                for btn_text in ["Log in", "Sign in", "Continue"]:
                    btns = page.locator(f"div.content:text-is('{btn_text}')")
                    if await btns.count() > 0:
                        app_state.log(f"点击文本为 '{btn_text}' 的按钮...")
                        await btns.first.click()
                        clicked = True
                        break
                    
                    btns = page.get_by_text(btn_text)
                    if await btns.count() > 0:
                        app_state.log(f"点击包含文本 '{btn_text}' 的元素...")
                        await btns.first.click()
                        clicked = True
                        break
                if not clicked:
                    app_state.log("无法点击登录按钮，尝试回车提交...")
                    await page.keyboard.press("Enter")
                
            app_state.log("等待登录跳转...")
            try:
                await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
                app_state.log("登录跳转成功")
            except:
                app_state.log("警告: 登录跳转超时，可能需要手动介入或验证码")

            app_state.log("尝试访问账号设置页获取 Token...")
            try:
                async with page.expect_response(lambda response: "GetUserToken" in response.url and response.status == 200, timeout=15000) as response_info:
                    await page.goto("https://www.trae.ai/account-setting#account")
                    await page.wait_for_load_state("networkidle")
                
                response = await response_info.value
                token_data = await response.json()
                
                token_path = os.path.join(GET_USER_TOKEN_DIR, f"{email}.json")
                with open(token_path, "w", encoding="utf-8") as f:
                    json.dump(token_data, f, ensure_ascii=False, indent=2)
                
                token_str = json.dumps(token_data, ensure_ascii=False)
                app_state.current_token = token_str
                
                # Get and save cookies
                cookies = await context.cookies()
                cookie_path = os.path.join(COOKIES_DIR, f"{email}.json")
                with open(cookie_path, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                
                cookie_str = json.dumps(cookies, ensure_ascii=False, indent=2)
                app_state.log("Token 获取成功！")
                app_state.log(f"Cookies 已保存到: {cookie_path}")
                app_state.log(f"Cookies 内容:\n{cookie_str}")
                
                # Broadcast token and cookies to websockets
                for ws in app_state.websockets.copy():
                    try:
                        asyncio.create_task(ws.send_json({
                            "type": "token", 
                            "token": token_str,
                            "cookies": cookie_str
                        }))
                    except:
                        app_state.websockets.discard(ws)
                
            except Exception as e:
                app_state.log(f"获取 Token 失败: {e}")
                screenshot_path = os.path.join(BASE_DIR, "error_screenshot.png")
                await page.screenshot(path=screenshot_path)
                app_state.log(f"已保存错误截图至: {screenshot_path}")

        except Exception as e:
            app_state.log(f"流程出错: {e}")
        finally:
            app_state.log("关闭浏览器...")
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI Mode
        total = 1
        concurrency = 1
        try:
            total = int(sys.argv[1])
            if len(sys.argv) > 2:
                concurrency = int(sys.argv[2])
        except ValueError:
            print("Usage: python register.py [total] [concurrency]")
            sys.exit(1)
        asyncio.run(run_batch(total, concurrency))
    else:
        # Web Mode
        port = int(os.getenv("PORT", 8001))
        uvicorn.run(app, host="0.0.0.0", port=port)
