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
GET_USER_TOKEN_DIR = os.path.join(BASE_DIR, "GetUserToken")
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
        self.root.title("Trae Token 获取器")
        self.root.geometry("1100x700")
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
        
        self.btn_get_token = ModernButton(btn_frame, text="获取 Token", command=self.start_get_token)
        self.btn_get_token.pack(side="left")

        # Token Display
        token_frame = tk.LabelFrame(right_frame, text="Token", bg=COLOR_BG, fg=COLOR_TEXT_GRAY, font=("Segoe UI", 10, "bold"))
        token_frame.pack(fill="x", pady=(0, 10))
        
        self.txt_token = tk.Text(token_frame, height=4, bg=COLOR_LOG_BG, fg=COLOR_SUCCESS, font=FONT_MONO, relief="flat", padx=5, pady=5)
        self.txt_token.pack(fill="x", padx=5, pady=5)
        
        copy_btn = ModernButton(token_frame, text="复制 Token", command=self.copy_token, bg="#374151")
        copy_btn.pack(anchor="e", padx=5, pady=5)

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
            self.current_token = ""

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
        self.txt_token.delete("1.0", "end")
        
        threading.Thread(target=self.run_async_task, args=(email, pwd), daemon=True).start()

    def run_async_task(self, email, pwd):
        try:
            asyncio.run(self.get_token_logic(email, pwd))
        except Exception as e:
            print(f"任务异常: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_get_token.config(state="normal", bg=COLOR_ACCENT))

    async def get_token_logic(self, email, password):
        print(f"正在启动浏览器获取 {email} 的 Token...")
        # 使用 headless=False 让用户可以看到浏览器操作，方便排错
        # 也可以在 args 中添加 '--disable-blink-features=AutomationControlled' 来规避部分检测
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            try:
                # Login Flow
                print("正在打开登录页面...")
                await page.goto("https://www.trae.ai/login")
                
                print("正在输入账号密码...")
                try:
                     await page.wait_for_selector('input[type="email"]', timeout=10000)
                     await page.fill('input[type="email"]', email)
                except:
                     await page.get_by_role("textbox", name="Email").fill(email)

                # Check for password field
                try:
                    # Sometimes password field is not immediately visible or requires clicking "Continue"
                    if not await page.locator('input[type="password"]').is_visible():
                        print("检查是否需要点击继续...")
                        # 尝试点击可能的继续按钮
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
                    print(f"密码输入框查找失败: {e}")
                    # Fallback
                    await page.get_by_role("textbox", name="Password").fill(password)

                print("提交登录...")
                # Submit
                try:
                    # 优先尝试用户提供的特定类名
                    if await page.locator('.btn-submit').is_visible():
                        print("检测到 .btn-submit 按钮，点击...")
                        await page.locator('.btn-submit').click()
                    # 尝试标准 submit 按钮
                    elif await page.locator('button[type="submit"]').is_visible():
                         await page.click('button[type="submit"]')
                    else:
                        raise Exception("未找到常规提交按钮")
                except Exception as e:
                    print(f"常规点击失败 ({e})，尝试文本匹配...")
                    # Fallback text search
                    clicked = False
                    for btn_text in ["Log in", "Sign in", "Continue"]:
                        # 精确匹配 div 内容
                        btns = page.locator(f"div.content:text-is('{btn_text}')")
                        if await btns.count() > 0:
                            print(f"点击文本为 '{btn_text}' 的按钮...")
                            await btns.first.click()
                            clicked = True
                            break
                        
                        # 模糊匹配
                        btns = page.get_by_text(btn_text)
                        if await btns.count() > 0:
                            print(f"点击包含文本 '{btn_text}' 的元素...")
                            await btns.first.click()
                            clicked = True
                            break
                    if not clicked:
                        print("无法点击登录按钮，尝试回车提交...")
                        await page.keyboard.press("Enter")
                
                print("等待登录跳转...")
                # 等待 URL 变化或特定的登录后元素出现，确保登录成功
                try:
                    # 假设登录成功后 URL 不会包含 login
                    await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
                    print("登录跳转成功")
                except:
                    print("警告: 登录跳转超时，可能需要手动介入或验证码")

                # 主动去获取 Token
                print("尝试访问账号设置页获取 Token...")
                try:
                    async with page.expect_response(lambda response: "GetUserToken" in response.url and response.status == 200, timeout=15000) as response_info:
                        await page.goto("https://www.trae.ai/account-setting#account")
                        # 确保页面加载
                        await page.wait_for_load_state("networkidle")
                    
                    response = await response_info.value
                    token_data = await response.json()
                    
                    # Save to file
                    token_path = os.path.join(GET_USER_TOKEN_DIR, f"{email}.json")
                    with open(token_path, "w", encoding="utf-8") as f:
                        json.dump(token_data, f, ensure_ascii=False, indent=2)
                    
                    # Display
                    token_str = json.dumps(token_data, ensure_ascii=False)
                    self.current_token = token_str
                    self.root.after(0, lambda: self.display_token(token_str))
                    print("Token 获取成功！")
                    
                except Exception as e:
                    print(f"获取 Token 失败: {e}")
                    # 截图保存以供调试
                    screenshot_path = os.path.join(BASE_DIR, "error_screenshot.png")
                    await page.screenshot(path=screenshot_path)
                    print(f"已保存错误截图至: {screenshot_path}")

            except Exception as e:
                print(f"流程出错: {e}")
            finally:
                print("关闭浏览器...")
                await browser.close()

    def display_token(self, token_text):
        self.txt_token.delete("1.0", "end")
        self.txt_token.insert("end", token_text)

    def copy_token(self):
        token = self.txt_token.get("1.0", "end-1c")
        if token:
            self.root.clipboard_clear()
            self.root.clipboard_append(token)
            messagebox.showinfo("成功", "Token 已复制到剪贴板")

if __name__ == "__main__":
    root = tk.Tk()
    app = TokenManagerApp(root)
    root.mainloop()
