import httpx
import random
import string
import re
import asyncio

# Config
API_BASE_URL = "https://api.mail.cx/api/v1"
KNOWN_DOMAINS = ["uuf.me", "nqmo.com", "end.tw"]

class AsyncMailClient:
    def __init__(self):
        self.client = None
        self.email_address = None
        self.processed_ids = set()
        self.api_token = None
        self.api_headers = {}
        self.last_verification_code = None

    async def start(self):
        """Initialize Async HTTP Client"""
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=30.0
        )
        print("邮箱客户端已初始化...")
        await self._authenticate()

    async def _authenticate(self):
        """Get API Token"""
        url = f"{API_BASE_URL}/auth/authorize_token"
        try:
            response = await self.client.post(url, json={})
            if response.status_code == 200:
                token = response.json()
                if isinstance(token, dict):
                    token = token.get("token") or token.get("access_token") or token.get("data")
                if isinstance(token, str):
                    token = token.strip().strip("\"")
                
                self.api_token = token
                if self.api_token:
                    self.api_headers = {"Authorization": f"Bearer {self.api_token}"}
                else:
                    print("邮箱认证失败：未获取到 token")
            else:
                print(f"邮箱认证失败：HTTP {response.status_code}")
        except Exception as e:
            print(f"邮箱认证异常：{e}")

    def get_email(self):
        """Generate Temp Email"""
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        domain = random.choice(KNOWN_DOMAINS)
        self.email_address = f"{username}@{domain}"
        print(f"已生成邮箱：{self.email_address}")
        return self.email_address

    async def check_emails(self):
        """Check for new emails"""
        if not self.email_address:
            return

        api_url = f"{API_BASE_URL}/mailbox/{self.email_address}"
        try:
            response = await self.client.get(api_url, headers=self.api_headers)
            
            if response.status_code == 200:
                data = response.json()
                
                messages = []
                if isinstance(data, list):
                    messages = data
                elif isinstance(data, dict) and 'messages' in data:
                    messages = data['messages']
                
                # Process only the latest message
                if messages and len(messages) > 0:
                    latest_msg = messages[0]
                    # Only process if we haven't found a code yet or it's a new message ID
                    msg_id = latest_msg.get('id')
                    if not self.last_verification_code or (msg_id and msg_id not in self.processed_ids):
                         await self._process_message(latest_msg)

        except Exception as e:
            print(f"邮箱检查异常：{e}")

    async def _process_message(self, msg):
        if not isinstance(msg, dict):
            return

        msg_id = msg.get('id')
        if msg_id:
            subject = msg.get('subject', 'No Subject')
            print(f"\n新邮件：{subject}")
            await self._fetch_and_parse_content(msg_id)
            self.processed_ids.add(msg_id)

    async def _fetch_and_parse_content(self, msg_id):
        url = f"{API_BASE_URL}/mailbox/{self.email_address}/{msg_id}"
        try:
            response = await self.client.get(url, headers=self.api_headers)
            if response.status_code == 200:
                data = response.json()
                body = data.get('body', {})
                content = body.get('text', '') or body.get('html', '')
                self._parse_verification_code(content)
        except Exception as e:
            print(f"获取邮件内容异常：{e}")

    def _parse_verification_code(self, content):
        content_str = str(content)
        # Look for 6-digit code
        codes = re.findall(r'\b\d{6}\b', content_str)
        if codes:
            self.last_verification_code = codes[0]
            print(f"已找到验证码：{self.last_verification_code}")

    async def close(self):
        if self.client:
            await self.client.aclose()
