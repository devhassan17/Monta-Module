
# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class MontaStockSync(models.TransientModel):
    _name = "monta.stock.sync"
    _description = "Monta Stock Sync Helper"
    
    def _cron_sync_stock(self):
        api = self.env['monta.api']
        try:
            data = api.get_stock_levels()
        except Exception as e:
            _logger.exception("Stock fetch error: %s", e)
            return
        items = data.get('items') if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for item in items:
            sku = item.get('sku')
            if not sku:
                continue
            # Try to find product by monta_sku or default_code
            product = self.env['product.template'].search(['|', ('monta_sku', '=', sku), ('default_code', '=', sku)], limit=1)
            if not product:
                continue
            vals = {}
            if 'minStockLevel' in item:
                vals['monta_min_stock'] = item.get('minStockLevel') or 0.0
            if 'stockLevel' in item or 'quantity' in item:
                vals['monta_stock_level'] = item.get('stockLevel') or item.get('quantity') or 0.0
            if vals:
                product.write(vals)
                product.message_post(body=_("Monta stock sync: stock=%s, min=%s") % (vals.get('monta_stock_level'), vals.get('monta_min_stock')))
