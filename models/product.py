
# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    monta_product_id = fields.Char(string="Monta Product ID", copy=False, readonly=True)
    monta_sku = fields.Char(string="Monta SKU")
    monta_min_stock = fields.Float(string="Monta Min Stock", digits="Product Unit of Measure")
    monta_stock_level = fields.Float(string="Monta Stock Level", digits="Product Unit of Measure", readonly=True)
    is_monta_pack = fields.Boolean(string="Is Pack (send components to Monta)", default=False)
    
    def action_push_to_monta(self):
        for p in self:
            p._monta_push_product()
    
    def _get_monta_sku(self):
        self.ensure_one()
        return self.monta_sku or self.default_code or (self.barcode or str(self.id))
    
    def _monta_push_product(self):
        api = self.env['monta.api']
        for rec in self:
            payload = {
                "name": rec.name,
                "sku": rec._get_monta_sku(),
                "barcode": rec.barcode or "",
                "minStockLevel": rec.monta_min_stock or 0.0,
                "uom": rec.uom_id.name if rec.uom_id else "Units",
                "isPack": bool(rec.is_monta_pack),
            }
            if rec.monta_product_id:
                try:
                    api.update_product(rec.monta_product_id, payload)
                    rec.message_post(body=_("Updated product in Monta (ID %s).") % rec.monta_product_id)
                except Exception as e:
                    rec.message_post(body=_("Failed to update product in Monta: %s") % e, message_type='comment')
                    _logger.exception("Monta product update failed")
            else:
                try:
                    res = api.create_product(payload)
                    rec.monta_product_id = str(res.get('id') or res.get('productId') or '')
                    rec.monta_sku = res.get('sku') or payload['sku']
                    rec.message_post(body=_("Created product in Monta (ID %s).") % (rec.monta_product_id or '?'))
                except Exception as e:
                    rec.message_post(body=_("Failed to create product in Monta: %s") % e, message_type='comment')
                    _logger.exception("Monta product create failed")
