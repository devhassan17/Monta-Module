
# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timezone
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    monta_order_id = fields.Char(string="Monta Order ID", copy=False, readonly=True)
    monta_status = fields.Char(string="Monta Status", readonly=True, tracking=True)
    monta_reference = fields.Char(string="Monta Reference", readonly=True)
    monta_delivery_date = fields.Datetime(string="Monta Delivery Date", readonly=True, tracking=True)
    
    def _monta_prepare_order_payload(self):
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        lines = []
        for line in self.order_line:
            product = line.product_id.product_tmpl_id
            sku = product._get_monta_sku()
            qty = line.product_uom_qty
            # pack logic: if marked as pack, still send SKU; advanced explode could be added here
            lines.append({
                "sku": sku,
                "quantity": qty,
                "name": product.name,
            })
        payload = {
            "reference": self.name,
            "customer": {
                "name": partner.name,
                "email": partner.email or "",
                "phone": partner.phone or ""
            },
            "shippingAddress": {
                "name": partner.name,
                "street": partner.street or "",
                "street2": partner.street2 or "",
                "zip": partner.zip or "",
                "city": partner.city or "",
                "country": partner.country_id and partner.country_id.code or "",
            },
            "lines": lines,
        }
        return payload
    
    def action_push_to_monta(self):
        api = self.env['monta.api']
        for so in self:
            # Ensure products exist
            for line in so.order_line:
                tmpl = line.product_id.product_tmpl_id
                if not tmpl.monta_product_id:
                    try:
                        tmpl._monta_push_product()
                    except Exception as e:
                        so.message_post(body=_("Failed to push product %s to Monta: %s") % (tmpl.display_name, e))
            payload = so._monta_prepare_order_payload()
            try:
                res = api.create_order(payload)
                so.monta_order_id = str(res.get('id') or res.get('orderId') or '')
                so.monta_status = res.get('status') or 'created'
                so.monta_reference = res.get('reference') or so.name
                so.message_post(body=_("Pushed order to Monta (ID %s).") % (so.monta_order_id or '?'))
                _logger.info("Order %s pushed to Monta ID %s", so.name, so.monta_order_id)
            except Exception as e:
                so.message_post(body=_("Failed to push order to Monta: %s") % e)
                _logger.exception("Monta order create failed")
    
    def _cron_fetch_orders(self):
        api = self.env['monta.api']
        # fetch recently updated orders from last 3 hours
        since = datetime.now(timezone.utc) - fields.DateUtils.relativedelta(hours=3)
        try:
            data = api.get_orders_updated_since(since.isoformat())
        except Exception as e:
            _logger.exception("Fetch Monta orders failed: %s", e)
            return
        # Assume data is a list of orders
        if isinstance(data, dict) and data.get('items'):
            orders = data['items']
        else:
            orders = data if isinstance(data, list) else []
        for item in orders:
            ref = item.get('reference')
            if not ref:
                continue
            so = self.search([('name', '=', ref)], limit=1)
            if not so:
                continue
            old_status = so.monta_status
            so.write({
                'monta_order_id': str(item.get('id') or item.get('orderId') or so.monta_order_id or ''),
                'monta_status': item.get('status') or old_status,
            })
            # detect delivery
            if (item.get('status') or '').lower() in ('delivered', 'shipped', 'completed'):
                # mark Odoo as delivered: confirm pickings done
                for picking in so.picking_ids.filtered(lambda p: p.state not in ('done','cancel')):
                    try:
                        for ml in picking.move_line_ids:
                            if ml.qty_done == 0:
                                ml.qty_done = ml.product_uom_qty
                        picking.button_validate()
                    except Exception as e:
                        _logger.warning("Could not validate picking for %s: %s", so.name, e)
                # Set delivery date
                delivered_at = item.get('deliveredAt') or item.get('shippedAt') or item.get('completedAt')
                if delivered_at:
                    so.monta_delivery_date = fields.Datetime.from_string(delivered_at)
                # Update Odoo order state if needed
                if so.state not in ('sale','done'):
                    so.action_confirm()
                so.message_post(body=_("Monta marked delivered; Odoo delivery validated."))
