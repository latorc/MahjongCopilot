""" Python wrapper for MJAPI online model
API 文档: https://pastebin.com/wks80EsZ
密码: EaSXeZycr4
把文档内容粘贴到测试网址: https://editor.swagger.io/"""

import requests

class MJAPI_Client:
    def __init__(self, base_url:str, timeout:float=5):
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {}

    def set_bearer_token(self, token):
        """Set the bearer token for authentication."""
        self.headers['Authorization'] = f'Bearer {token}'

    def register(self, name):
        """Register a new user with a name."""
        url = f'{self.base_url}/user/register'
        data = {'name': name}
        response = requests.post(url, json=data)
        return response.json()

    def login(self, name, secret):
        """Login with name and secret."""
        url = f'{self.base_url}/user/login'
        data = {'name': name, 'secret': secret}
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

    def get_user_info(self):
        """Get current user info."""
        url = f'{self.base_url}/user'        
        response = requests.get(url, headers=self.headers)
        print(url, self.headers, response)
        return response.json()

    def logout(self):
        """Logout the current user."""
        url = f'{self.base_url}/user/logout'
        response = requests.post(url, headers=self.headers)
        return response.json()

    def list_models(self):
        """Get available models."""
        url = f'{self.base_url}/mjai/list'
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_usage(self):
        """Get mjai query usage."""
        url = f'{self.base_url}/mjai/usage'
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_limit(self):
        """Get mjai query limit."""
        url = f'{self.base_url}/mjai/limit'
        response = requests.get(url, headers=self.headers)
        return response.json()

    def start_bot(self, id, bound, model):
        """Start mjai bot with specified parameters."""
        url = f'{self.base_url}/mjai/start'
        data = {'id': id, 'bound': bound, 'model': model}
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

    def act(self, seq, data) -> dict:
        """Query mjai bot with a single action. returns reaction dict /None"""
        url = f'{self.base_url}/mjai/act'
        data = {'seq': seq, 'data': data}
        response = requests.post(url, json=data, headers=self.headers, timeout=self.timeout)
        if not response.content:
            return None
        else:
            return response.json()['act']


    def batch(self, actions):
        """Query mjai bot with multiple actions."""
        url = f'{self.base_url}/mjai/batch'
        response = requests.post(url, json=actions, headers=self.headers)
        return response.json()

    def stop_bot(self) -> str:
        """Stop the mjai bot."""
        url = f'{self.base_url}/mjai/stop'
        response = requests.post(url, headers=self.headers)
        return response.content.decode()