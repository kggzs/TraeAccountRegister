import asyncio
import os
import json
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from playwright.async_api import async_playwright

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
GET_USER_TOKEN_DIR = os.path.join(BASE_DIR, "GetUserToken")
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(GET_USER_TOKEN_DIR, exist_ok=True)

# --- UI Constants ---
COLOR_BG = "#111827"         # Main Background
COLOR_CARD = "#1f2937"       # Card Background
COLOR_ACCENT = "#6366f1"     # Primary Button / Progress
COLOR_ACCENT_HOVER = "#4f46e5"
COLOR_TEXT = "#f3f4f6"       # Primary Text
COLOR_TEXT_GRAY = "#9ca3af"  # Secondary Text
COLOR_SUCCESS = "#10b981"    # Success Green
COLOR_FAIL = "#ef4444"       # Fail Red
COLOR_WARNING = "#f59e0b"   # Warning Orange
COLOR_LOG_BG = "#0f172a"     # Log Background
COLOR_BORDER = "#374151"     # Border color

FONT_MAIN = ("Segoe UI", 12)
FONT_HEADER = ("Segoe UI", 20, "bold")
FONT_MONO = ("Consolas", 11)

class TextRedirector:
    def __init__(self, widget, root):
        self.widget = widget
        self.root = root

    def write(self, text):
        self.root.after(0, self._append_text, text)

    def _append_text(self, text):
        try:
            self.widget.configure(state="normal")
            self.widget.insert("end", text)
            self.widget.see("end")
            self.widget.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        pass

class ModernButton(tk.Button):
    def __init__(self, master, **kwargs):
        bg = kwargs.get('bg', COLOR_ACCENT)
        fg = kwargs.get('fg', 'white')
        kwargs['bg'] = bg
        kwargs['fg'] = fg
        kwargs['activebackground'] = kwargs.get('activebackground', COLOR_ACCENT_HOVER)
        kwargs['activeforeground'] = kwargs.get('activeforeground', 'white')
        kwargs['relief'] = 'flat'
        kwargs['bd'] = 0
        kwargs['font'] = FONT_MAIN
        kwargs['cursor'] = 'hand2'
        super().__init__(master, **kwargs)

class TokenManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trae Token & Cookies 获取器")
        self.root.geometry("1200x800")
        self.root.configure(bg=COLOR_BG)
        
        # Windows Dark Mode
        try:
            from ctypes import windll, byref, c_int
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0: hwnd = self.root.winfo_id()
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(2)), 4)
        except Exception:
            pass

        self.accounts = []
        self.is_running = False
        self.current_token = ""
        self.current_cookies = ""

        self._setup_ui()
        self.load_accounts()
        
        # Redirect stdout
        self.redirector = TextRedirector(self.log_area, root)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

    def _setup_ui(self):
        # Layout: Left (List), Right (Details + Log)
        paned = tk.PanedWindow(self.root, orient="horizontal", bg=COLOR_BG, sashwidth=4)
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Side
        left_frame = tk.Frame(paned, bg=COLOR_BG)
        paned.add(left_frame, width=300)

        tk.Label(left_frame, text="账号列表", bg=COLOR_BG, fg=COLOR_TEXT, font=FONT_HEADER).pack(anchor="w", pady=(0, 10))
        
        # Listbox with Scrollbar
        list_scroll = tk.Scrollbar(left_frame)
        list_scroll.pack(side="right", fill="y")
        
        self.account_listbox = tk.Listbox(left_frame, bg=COLOR_LOG_BG, fg=COLOR_TEXT, 
                                          selectbackground=COLOR_ACCENT, selectforeground="white",
                                          font=FONT_MAIN, relief="flat", bd=0,
                                          yscrollcommand=list_scroll.set)
        self.account_listbox.pack(side="left", fill="both", expand=True)
        list_scroll.config(command=self.account_listbox.yview)
        
        self.account_listbox.bind("<<ListboxSelect>>", self.on_account_select)
        self.account_listbox.bind("<Double-Button-1>", lambda event: self.start_get_token())

        # Right Side
        right_frame = tk.Frame(paned, bg=COLOR_BG, padx=20)
        paned.add(right_frame)

        # Selected Account Info
        info_frame = tk.LabelFrame(right_frame, text="当前账号", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=("Segoe UI", 10, "bold"))
        info_frame.pack(fill="x", pady=(0, 10))

        grid_frame = tk.Frame(info_frame, bg=COLOR_BG, pady=10, padx=10)
        grid_frame.pack(fill="x")
        
        tk.Label(grid_frame, text="Email:", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=FONT_MAIN).grid(row=0, column=0, sticky="w", padx=5)
        self.var_email = tk.StringVar()
        tk.Entry(grid_frame, textvariable=self.var_email, bg=COLOR_CARD, fg=COLOR_TEXT, relief="flat", readonlybackground=COLOR_CARD, state="readonly", font=FONT_MAIN).grid(row=0, column=1, sticky="ew", padx=5)
        
        tk.Label(grid_frame, text="Password:", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=FONT_MAIN).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.var_pwd = tk.StringVar()
        tk.Entry(grid_frame, textvariable=self.var_pwd, bg=COLOR_CARD, fg=COLOR_TEXT, relief="flat", readonlybackground=COLOR_CARD, state="readonly", font=FONT_MAIN, show="*").grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        grid_frame.columnconfigure(1, weight=1)

        # Actions
        btn_frame = tk.Frame(right_frame, bg=COLOR_BG)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.btn_get_token = ModernButton(btn_frame, text="🔑 获取 Token & Cookies", command=self.start_get_token, width=25)
        self.btn_get_token.pack(side="left", padx=(0, 10))
        
        status_label = tk.Label(btn_frame, text="状态: 就绪", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=("Segoe UI", 10))
        status_label.pack(side="left")
        self.status_label = status_label

        # Token Display
        token_frame = tk.LabelFrame(right_frame, text="Token", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=("Segoe UI", 10, "bold"))
        token_frame.pack(fill="x", pady=(0, 10))
        
        self.txt_token = tk.Text(token_frame, height=4, bg=COLOR_LOG_BG, fg=COLOR_SUCCESS, font=FONT_MONO, relief="flat", padx=5, pady=5, wrap="word")
        self.txt_token.pack(fill="x", padx=5, pady=5)
        
        copy_token_btn = ModernButton(token_frame, text="复制 Token", command=self.copy_token, bg="#374151")
        copy_token_btn.pack(anchor="e", padx=5, pady=5)
        
        # Cookies Display
        cookies_frame = tk.LabelFrame(right_frame, text="Cookies", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=("Segoe UI", 10, "bold"))
        cookies_frame.pack(fill="x", pady=(0, 10))
        
        self.txt_cookies = tk.Text(cookies_frame, height=4, bg=COLOR_LOG_BG, fg=COLOR_SUCCESS, font=FONT_MONO, relief="flat", padx=5, pady=5, wrap="word")
        self.txt_cookies.pack(fill="x", padx=5, pady=5)
        
        copy_cookies_btn = ModernButton(cookies_frame, text="复制 Cookies", command=self.copy_cookies, bg="#374151")
        copy_cookies_btn.pack(anchor="e", padx=5, pady=5)

        # Log Area
        log_frame = tk.LabelFrame(right_frame, text="工作日志", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=("Segoe UI", 10, "bold"))
        log_frame.pack(fill="both", expand=True)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, bg=COLOR_LOG_BG, fg="#d1d5db", 
                                                 font=FONT_MONO, relief="flat", state='disabled', padx=10, pady=10)
        self.log_area.pack(fill="both", expand=True)

    def load_accounts(self):
        if not os.path.exists(ACCOUNTS_FILE):
            print("未找到 accounts.txt")
            return
        
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            self.accounts = []
            # Skip header if present
            start_idx = 0
            if lines and "Email" in lines[0] and "Password" in lines[0]:
                start_idx = 1
            
            for line in lines[start_idx:]:
                parts = line.strip().split()
                if len(parts) >= 2:
                    email = parts[0]
                    pwd = parts[1]
                    self.accounts.append((email, pwd))
                    self.account_listbox.insert("end", email)
            
            print(f"已加载 {len(self.accounts)} 个账号")
            
        except Exception as e:
            print(f"加载账号失败: {e}")

    def on_account_select(self, event):
        selection = self.account_listbox.curselection()
        if selection:
            index = selection[0]
            email, pwd = self.accounts[index]
            self.var_email.set(email)
            self.var_pwd.set(pwd)
            self.txt_token.delete("1.0", "end")
            self.txt_cookies.delete("1.0", "end")
            self.current_token = ""
            self.current_cookies = ""
            self.status_label.config(text="状态: 就绪", fg=COLOR_TEXT_GRAY)

    def start_get_token(self):
        email = self.var_email.get()
        pwd = self.var_pwd.get()
        
        if not email or not pwd:
            messagebox.showwarning("提示", "请先选择一个账号")
            return
            
        if self.is_running:
            return

        self.is_running = True
        self.btn_get_token.config(state="disabled", bg="#4b5563")
        self.status_label.config(text="状态: 运行中...", fg=COLOR_WARNING)
        self.txt_token.delete("1.0", "end")
        self.txt_cookies.delete("1.0", "end")
        self.current_token = ""
        self.current_cookies = ""
        
        threading.Thread(target=self.run_async_task, args=(email, pwd), daemon=True).start()

    def run_async_task(self, email, pwd):
        try:
            asyncio.run(self.get_token_logic(email, pwd))
        except Exception as e:
            print(f"任务异常: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_get_token.config(state="normal", bg=COLOR_ACCENT))
            self.root.after(0, lambda: self.status_label.config(text="状态: 就绪", fg=COLOR_TEXT_GRAY))

    async def get_token_logic(self, email, password):
        """Get token logic - 从 register.py 复制并优化，已优化速度"""
        print(f"正在启动浏览器获取 {email} 的 Token...")
        
        async with async_playwright() as p:
            # 优化浏览器启动参数，加快速度
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-ipc-flooding-protection',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps',
                ]
            )
            # 优化上下文，禁用图片和CSS以加快速度
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                # 禁用图片、字体、CSS等资源加载以加快速度
                ignore_https_errors=True,
            )
            
            page = await context.new_page()
            
            # 拦截并阻止图片、字体等非必要资源加载，保留CSS和脚本以确保页面正常工作
            # 注意：只在页面加载后启用拦截，避免干扰初始加载
            async def handle_route(route):
                resource_type = route.request.resource_type
                url = route.request.url
                # 只阻止图片、字体、媒体文件，保留CSS和脚本
                # 同时保留 trae.ai 域名的所有资源，确保网站正常工作
                if 'trae.ai' in url:
                    await route.continue_()
                elif resource_type in ['image', 'font', 'media']:
                    await route.abort()
                else:
                    await route.continue_()
            
            await page.route('**/*', handle_route)

            try:
                print("正在打开登录页面...")
                # 等待页面加载完成，确保脚本执行完毕
                await page.goto("https://www.trae.ai/login", wait_until="networkidle", timeout=30000)
                # 额外等待一下确保页面完全渲染
                await page.wait_for_timeout(1000)
                
                print("正在输入账号密码...")
                # 等待邮箱输入框出现并可见
                try:
                    await page.wait_for_selector('input[type="email"]', state="visible", timeout=10000)
                    # 确保元素可交互
                    await page.wait_for_timeout(500)
                    await page.fill('input[type="email"]', email)
                    print(f"✅ 已输入邮箱: {email}")
                except Exception as e:
                    print(f"尝试通过选择器输入邮箱失败: {e}，尝试备用方法...")
                    try:
                        await page.get_by_role("textbox", name="Email").fill(email)
                        print(f"✅ 已通过备用方法输入邮箱: {email}")
                    except Exception as e2:
                        print(f"❌ 输入邮箱失败: {e2}")
                        raise

                # 输入密码
                try:
                    # 先检查密码框是否可见
                    password_visible = await page.locator('input[type="password"]').is_visible()
                    if not password_visible:
                        print("检查是否需要点击继续...")
                        # 等待一下让页面响应
                        await page.wait_for_timeout(1000)
                        btns = page.locator('button')
                        count = await btns.count()
                        for i in range(count):
                            try:
                                txt = await btns.nth(i).inner_text()
                                if "continue" in txt.lower() or "next" in txt.lower():
                                    print(f"点击继续按钮: {txt}")
                                    await btns.nth(i).click()
                                    await page.wait_for_timeout(1000)
                                    break
                            except:
                                continue
                    
                    # 等待密码输入框出现并可见
                    await page.wait_for_selector('input[type="password"]', state="visible", timeout=10000)
                    await page.wait_for_timeout(500)
                    await page.fill('input[type="password"]', password)
                    print("✅ 已输入密码")
                except Exception as e:
                    print(f"尝试通过选择器输入密码失败: {e}，尝试备用方法...")
                    try:
                        await page.get_by_role("textbox", name="Password").fill(password)
                        print("✅ 已通过备用方法输入密码")
                    except Exception as e2:
                        print(f"❌ 输入密码失败: {e2}")
                        raise

                print("提交登录...")
                await page.wait_for_timeout(500)  # 等待一下确保输入完成
                try:
                    # 尝试多种方式点击登录按钮
                    clicked = False
                    
                    # 方法1: .btn-submit
                    try:
                        if await page.locator('.btn-submit').is_visible():
                            print("检测到 .btn-submit 按钮，点击...")
                            await page.locator('.btn-submit').click()
                            clicked = True
                            print("✅ 已点击 .btn-submit 按钮")
                    except:
                        pass
                    
                    # 方法2: button[type="submit"]
                    if not clicked:
                        try:
                            if await page.locator('button[type="submit"]').is_visible():
                                print("检测到 submit 按钮，点击...")
                                await page.click('button[type="submit"]')
                                clicked = True
                                print("✅ 已点击 submit 按钮")
                        except:
                            pass
                    
                    # 方法3: 文本匹配
                    if not clicked:
                        for btn_text in ["Log in", "Sign in", "Continue", "登录"]:
                            try:
                                btns = page.locator(f"div.content:text-is('{btn_text}')")
                                if await btns.count() > 0:
                                    print(f"点击文本为 '{btn_text}' 的按钮...")
                                    await btns.first.click()
                                    clicked = True
                                    print(f"✅ 已点击 '{btn_text}' 按钮")
                                    break
                            except:
                                pass
                            
                            if not clicked:
                                try:
                                    btns = page.get_by_text(btn_text)
                                    if await btns.count() > 0:
                                        print(f"点击包含文本 '{btn_text}' 的元素...")
                                        await btns.first.click()
                                        clicked = True
                                        print(f"✅ 已点击包含 '{btn_text}' 的元素")
                                        break
                                except:
                                    pass
                    
                    # 方法4: 回车提交
                    if not clicked:
                        print("无法找到登录按钮，尝试回车提交...")
                        await page.keyboard.press("Enter")
                        clicked = True
                        print("✅ 已按回车提交")
                    
                    if clicked:
                        await page.wait_for_timeout(1000)  # 等待提交响应
                    
                except Exception as e:
                    print(f"❌ 提交登录失败: {e}")
                    raise
                
                print("等待登录跳转...")
                try:
                    # 减少等待时间
                    await page.wait_for_url(lambda url: "login" not in url, timeout=10000)
                    print("登录跳转成功")
                except:
                    print("警告: 登录跳转超时，可能需要手动介入或验证码")

                print("尝试访问账号设置页获取 Token...")
                try:
                    # 使用更快的加载策略，只等待响应，不等待所有资源加载
                    async with page.expect_response(lambda response: "GetUserToken" in response.url and response.status == 200, timeout=10000) as response_info:
                        await page.goto("https://www.trae.ai/account-setting#account", wait_until="domcontentloaded", timeout=30000)
                        # 不等待 networkidle，只等待 DOM 加载完成即可
                    
                    response = await response_info.value
                    token_data = await response.json()
                    
                    token_path = os.path.join(GET_USER_TOKEN_DIR, f"{email}.json")
                    with open(token_path, "w", encoding="utf-8") as f:
                        json.dump(token_data, f, ensure_ascii=False, indent=2)
                    
                    token_str = json.dumps(token_data, ensure_ascii=False)
                    self.current_token = token_str
                    self.root.after(0, lambda: self.display_token(token_str))
                    print("✅ Token 获取成功！")
                    
                    # Get and save cookies
                    cookies = await context.cookies()
                    cookie_path = os.path.join(COOKIES_DIR, f"{email}.json")
                    with open(cookie_path, "w", encoding="utf-8") as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                    
                    cookie_str = json.dumps(cookies, ensure_ascii=False, indent=2)
                    self.current_cookies = cookie_str
                    self.root.after(0, lambda: self.display_cookies(cookie_str))
                    print(f"✅ Cookies 已保存到: {cookie_path}")
                    print(f"📋 Cookies 内容:\n{cookie_str}")
                    
                    # Update status to success
                    self.root.after(0, lambda: self.status_label.config(text="状态: 获取成功 ✅", fg=COLOR_SUCCESS))
                    
                except Exception as e:
                    print(f"❌ 获取 Token 失败: {e}")
                    screenshot_path = os.path.join(BASE_DIR, "error_screenshot.png")
                    await page.screenshot(path=screenshot_path)
                    print(f"已保存错误截图至: {screenshot_path}")
                    self.root.after(0, lambda: self.status_label.config(text="状态: 获取失败 ❌", fg=COLOR_FAIL))

            except Exception as e:
                print(f"❌ 流程出错: {e}")
                self.root.after(0, lambda: self.status_label.config(text="状态: 获取失败 ❌", fg=COLOR_FAIL))
            finally:
                print("关闭浏览器...")
                await browser.close()

    def display_token(self, token_text):
        self.txt_token.delete("1.0", "end")
        self.txt_token.insert("end", token_text)

    def display_cookies(self, cookies_text):
        self.txt_cookies.delete("1.0", "end")
        self.txt_cookies.insert("end", cookies_text)

    def copy_token(self):
        token = self.txt_token.get("1.0", "end-1c")
        if token and token.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(token)
            messagebox.showinfo("成功", "Token 已复制到剪贴板")
        else:
            messagebox.showwarning("提示", "Token 为空，请先获取 Token")

    def copy_cookies(self):
        cookies = self.txt_cookies.get("1.0", "end-1c")
        if cookies and cookies.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(cookies)
            messagebox.showinfo("成功", "Cookies 已复制到剪贴板")
        else:
            messagebox.showwarning("提示", "Cookies 为空，请先获取 Cookies")

if __name__ == "__main__":
    root = tk.Tk()
    app = TokenManagerApp(root)
    root.mainloop()
