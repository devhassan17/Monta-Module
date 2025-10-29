
# -*- coding: utf-8 -*-
import logging
import json
import requests
from odoo import models, fields, _

_logger = logging.getLogger(__name__)

class MontaAPIError(Exception):
    pass

class MontaAPI(models.AbstractModel):
    _name = "monta.api"
    _description = "Monta API Helper (v6)"
    
    def _get_cfg(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'base_url': ICP.get_param('monta.base_url', default='https://api-v6.monta.nl'),
            'username': ICP.get_param('monta.username') or '',
            'password': ICP.get_param('monta.password') or '',
            'client_id': ICP.get_param('monta.client_id') or '',
            'client_secret': ICP.get_param('monta.client_secret') or '',
            'timeout': int(ICP.get_param('monta.timeout', default='30') or '30'),
            'inbound_enabled': ICP.get_param('monta.inbound_enabled', default='1') == '1',
        }
    
    # Token cache in-memory per env registry
    _token = None
    
    def _get_headers(self):
        cfg = self._get_cfg()
        headers = {'Accept': 'application/json', 'User-Agent': 'Odoo/18 Monta Integration Lite'}
        # Prefer OAuth2 token if available
        if cfg.get('client_id') and cfg.get('client_secret'):
            if not self._token:
                self._token = self._fetch_token(cfg)
            headers['Authorization'] = f"Bearer {self._token}"
        elif cfg.get('username') and cfg.get('password'):
            # Some Monta v6 client libs use basic auth with username/password
            # We will attach via HTTPBasicAuth inside request
            pass
        else:
            raise MontaAPIError(_("Monta credentials are missing. Configure in Settings."))
        return headers
    
    def _fetch_token(self, cfg):
        url = cfg['base_url'].rstrip('/') + '/auth/token'
        payload = {'clientId': cfg['client_id'], 'clientSecret': cfg['client_secret']}
        try:
            resp = requests.post(url, json=payload, timeout=cfg['timeout'])
            if resp.status_code >= 400:
                raise MontaAPIError(_("Token request failed %s: %s") % (resp.status_code, resp.text))
            data = resp.json()
            token = data.get('accessToken') or data.get('access_token')
            if not token:
                raise MontaAPIError(_("Token not found in response."))
            return token
        except requests.RequestException as e:
            raise MontaAPIError(_("Token request error: %s") % e)
    
    # --- Generic HTTP helpers
    def _req(self, method, path, payload=None, params=None):
        cfg = self._get_cfg()
        base = cfg['base_url'].rstrip('/')
        url = f"{base}{path if path.startswith('/') else '/' + path}"
        headers = self._get_headers()
        auth = None
        if not headers.get('Authorization') and cfg.get('username') and cfg.get('password'):
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(cfg['username'], cfg['password'])
        
        try:
            resp = requests.request(method, url, json=payload, params=params, headers=headers, auth=auth, timeout=cfg['timeout'])
            if resp.status_code == 401 and cfg.get('client_id'):
                # Maybe token expired; retry once
                self._token = None
                headers = self._get_headers()
                resp = requests.request(method, url, json=payload, params=params, headers=headers, auth=auth, timeout=cfg['timeout'])
            if resp.status_code >= 400:
                raise MontaAPIError(_("Monta API %s %s failed %s: %s") % (method, url, resp.status_code, resp.text))
            if resp.text:
                return resp.json()
            return {}
        except requests.RequestException as e:
            raise MontaAPIError(_("HTTP error with Monta: %s") % e)
    
    # --- Specific endpoints (names follow common WMS patterns)
    def get_health(self):
        return self._req('GET', '/health')
    
    # Orders
    def create_order(self, payload):
        return self._req('POST', '/order', payload)
    
    def get_order(self, order_id):
        return self._req('GET', f'/order/{order_id}')
    
    def find_order(self, ref):
        return self._req('GET', '/order', params={'reference': ref})
    
    def get_orders_updated_since(self, updated_from_iso):
        return self._req('GET', '/order', params={'fromUpdatedDate': updated_from_iso})
    
    # Products
    def create_product(self, payload):
        return self._req('POST', '/product', payload)
    
    def get_product_by_sku(self, sku):
        return self._req('GET', '/product', params={'sku': sku})
    
    def update_product(self, product_id, payload):
        return self._req('PATCH', f'/product/{product_id}', payload)
    
    # Suppliers
    def create_supplier(self, payload):
        return self._req('POST', '/supplier', payload)
    
    def find_supplier(self, ref):
        return self._req('GET', '/supplier', params={'reference': ref})
    
    # Inbound (PO)
    def create_inbound(self, payload):
        return self._req('POST', '/inbound', payload)
    
    def update_inbound(self, inbound_id, payload):
        return self._req('PATCH', f'/inbound/{inbound_id}', payload)
    
    # Stock
    def get_stock_levels(self, params=None):
        return self._req('GET', '/stock', params=params or {})
