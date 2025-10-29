
# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    monta_inbound_id = fields.Char(string="Monta Inbound ID", copy=False, readonly=True)
    monta_inbound_status = fields.Char(string="Monta Inbound Status", readonly=True, tracking=True)
    
    def _monta_prepare_inbound_payload(self):
        self.ensure_one()
        supplier = self.partner_id
        lines = []
        for line in self.order_line:
            tmpl = line.product_id.product_tmpl_id
            sku = tmpl._get_monta_sku()
            lines.append({
                "sku": sku,
                "quantity": line.product_qty,
                "name": tmpl.name,
            })
        payload = {
            "reference": self.name,
            "supplier": {
                "name": supplier.name,
                "reference": supplier.ref or supplier.id,
                "email": supplier.email or "",
                "phone": supplier.phone or ""
            },
            "lines": lines
        }
        return payload
    
    def action_push_inbound_to_monta(self):
        api = self.env['monta.api']
        for po in self:
            # Ensure supplier exists in Monta
            supplier_ref = po.partner_id.ref or po.partner_id.id
            try:
                found = api.find_supplier(supplier_ref)
            except Exception as e:
                found = {}
            if not found:
                try:
                    api.create_supplier({
                        "name": po.partner_id.name,
                        "reference": supplier_ref,
                        "email": po.partner_id.email or "",
                        "phone": po.partner_id.phone or ""
                    })
                    po.message_post(body=_("Created supplier in Monta: %s") % po.partner_id.name)
                except Exception as e:
                    po.message_post(body=_("Failed to create supplier in Monta: %s") % e)
            
            # Ensure products exist
            for line in po.order_line:
                tmpl = line.product_id.product_tmpl_id
                if not tmpl.monta_product_id:
                    try:
                        tmpl._monta_push_product()
                    except Exception as e:
                        po.message_post(body=_("Failed to push product %s to Monta: %s") % (tmpl.display_name, e))
            
            payload = po._monta_prepare_inbound_payload()
            try:
                if po.monta_inbound_id:
                    res = self.env['monta.api'].update_inbound(po.monta_inbound_id, payload)
                    po.message_post(body=_("Updated inbound in Monta (ID %s).") % po.monta_inbound_id)
                else:
                    res = self.env['monta.api'].create_inbound(payload)
                    po.monta_inbound_id = str(res.get('id') or res.get('inboundId') or '')
                    po.monta_inbound_status = res.get('status') or 'created'
                    po.message_post(body=_("Created inbound in Monta (ID %s).") % (po.monta_inbound_id or '?'))
            except Exception as e:
                po.message_post(body=_("Failed to push inbound to Monta: %s") % e)
                _logger.exception("Monta inbound push failed")
