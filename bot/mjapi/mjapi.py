""" Python wrapper for MJAPI API
API 文档: https://pastebin.com/wks80EsZ
密码: EaSXeZycr4
把文档内容粘贴到测试网址: https://editor.swagger.io/"""

import requests

class MjapiClient:
    """ MJAPI API wrapper"""
    def __init__(self, base_url:str, timeout:float=5):
        self.base_url = base_url
        self.timeout = timeout
        self.token:str = None
        self.headers = {}

    def set_bearer_token(self, token):
        """Set the bearer token for authentication."""
        self.token = token
        self.headers['Authorization'] = f'Bearer {token}'
    
    def post_req(self, path:str, json=None, raise_error:bool=True):
        """ send POST to API and process response"""
        try:
            full_url = f'{self.base_url}{path}'
            res = requests.post(full_url, json=json, headers=self.headers, timeout=self.timeout)
            return self._process_res(res, raise_error)
        except requests.RequestException as e:
            if raise_error:
                raise e
            else:
                return None
    
    def get_req(self, path:str, raise_error:bool=True):
        """ send GET to API and process response"""
        try:
            full_url = f'{self.base_url}{path}'
            res = requests.get(full_url, headers=self.headers, timeout=self.timeout)
            return self._process_res(res, raise_error)
        except requests.RequestException as e:
            if raise_error:
                raise e
            else:
                return None
        
    def _process_res(self, res:requests.Response, raise_error:bool):
        """ return results or raise error"""            
        if res.ok:
            return res.json() if res.content else None
        elif 'error' in res.json():
            message = res.json()['error']
            if raise_error:
                raise RuntimeError(f"Error in response {res.status_code}: {message}")
            return res.json()
        else:
            raise RuntimeError(f"Unexpected API response {res.status_code}: {res.text}")
        
       

    def register(self, name):
        """Register a new user with a name."""
        path = '/user/register'
        data = {'name': name}
        res_json = self.post_req(path, json=data)
        return res_json

    def login(self, name, secret):
        """Login with name and secret. save token if success. otherwise raise error """
        path = '/user/login'
        data = {'name': name, 'secret': secret}
        res_json = self.post_req(path, json=data)
        if 'id' in res_json:
            self.token = res_json['id']
            self.set_bearer_token(self.token)
        else:
            raise RuntimeError(f"Error login: {res_json}")

    def get_user_info(self):
        """Get current user info."""
        path = '/user'
        res_json = self.get_req(path)
        return res_json

    def logout(self):
        """Logout the current user."""
        path = '/user/logout'
        res_json = self.post_req(path)
        return res_json

    def list_models(self) -> list[str]:
        """Return list of available models."""
        path = '/mjai/list'
        res_json = self.get_req(path)
        return res_json['models']

    def get_usage(self) -> int:
        """Get mjai query usage."""
        path = '/mjai/usage'
        res_json = self.get_req(path, None)
        return res_json['used']

    def get_limit(self):
        """Get mjai query limit."""
        path = '/mjai/limit'
        res_json = self.get_req(path, None)
        return res_json

    def start_bot(self, id, bound, model):
        """Start mjai bot with specified parameters."""
        path = '/mjai/start'
        data = {'id': id, 'bound': bound, 'model': model}
        res_json = self.post_req(path, json=data)
        return res_json

    def act(self, seq, data) -> dict | None:
        """Query mjai bot with a single action. returns reaction dict /None"""
        path = '/mjai/act'
        data = {'seq': seq, 'data': data}
        return self._post_act(path, seq, data)

    def batch(self, actions) -> dict | None:
        """Query mjai bot with multiple actions."""
        if len(actions) == 0:
            return None
        seq = actions[-1]['seq']
        path = '/mjai/batch'
        return self._post_act(path, seq, actions)

    def _post_act(self, path, _seq, actions):
        # post request to MJAPI and process response/errors
        response = requests.post(self.base_url + path, json=actions, headers=self.headers, timeout=self.timeout)
        if response.content:
            response_json = response.json()
            if response.status_code == 200:
                if 'act' in response_json:
                    # assume seq is correct
                    return response_json['act']
            elif 'error' in response_json:
                return response_json
            else:
                raise ValueError(f"status code {response.status_code}; {response.text}")
        elif response.status_code != 200:
            raise ValueError(f"status code {response.status_code}")
        return None

    def stop_bot(self):
        """Stop the mjai bot."""
        path = '/mjai/stop'
        res_json = self.post_req(path, None)
        return res_json
