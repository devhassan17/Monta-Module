
# -*- coding: utf-8 -*-
import requests

class MontaHttp:
    def __init__(self, base_url, timeout=30, token=None, username=None, password=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.token = token
        self.username = username
        self.password = password
    
    def _headers(self):
        h = {'Accept': 'application/json', 'User-Agent': 'Odoo/18 Monta Integration Lite'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h
    
    def request(self, method, path, json=None, params=None):
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        auth = None
        if not self.token and self.username and self.password:
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(self.username, self.password)
        r = requests.request(method, url, json=json, params=params, headers=self._headers(), timeout=self.timeout, auth=auth)
        r.raise_for_status()
        return r.json() if r.text else {}
