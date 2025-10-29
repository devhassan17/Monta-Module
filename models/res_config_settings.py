
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    
    monta_base_url = fields.Char(string="Monta API Base URL", default="https://api-v6.monta.nl")
    monta_username = fields.Char(string="Monta Username")
    monta_password = fields.Char(string="Monta Password")
    monta_client_id = fields.Char(string="Monta Client ID")
    monta_client_secret = fields.Char(string="Monta Client Secret")
    monta_timeout = fields.Integer(string="Monta Timeout (sec)", default=30)
    monta_inbound_enabled = fields.Boolean(string="Enable Inbound (PO) sync", default=True)
    
    def set_values(self):
        res = super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('monta.base_url', self.monta_base_url or 'https://api-v6.monta.nl')
        ICP.set_param('monta.username', self.monta_username or '')
        ICP.set_param('monta.password', self.monta_password or '')
        ICP.set_param('monta.client_id', self.monta_client_id or '')
        ICP.set_param('monta.client_secret', self.monta_client_secret or '')
        ICP.set_param('monta.timeout', str(self.monta_timeout or 30))
        ICP.set_param('monta.inbound_enabled', '1' if self.monta_inbound_enabled else '0')
        return res
    
    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            monta_base_url = ICP.get_param('monta.base_url', default='https://api-v6.monta.nl'),
            monta_username = ICP.get_param('monta.username'),
            monta_password = ICP.get_param('monta.password'),
            monta_client_id = ICP.get_param('monta.client_id'),
            monta_client_secret = ICP.get_param('monta.client_secret'),
            monta_timeout = int(ICP.get_param('monta.timeout', default='30') or '30'),
            monta_inbound_enabled = ICP.get_param('monta.inbound_enabled', default='1') == '1',
        )
        return res
