# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_open_monta_order_status(self):
        """Open Monta order status records for this Sale Order.

        Robustly resolves the action XMLID across possible module technical names.
        Falls back to a runtime action if no XMLID is found, avoiding RPC errors.
        """
        self.ensure_one()

        candidate_xmlids = [
            # Common variations of the module technical name:
            "Monta-Module.action_monta_order_status",
            "Monta_Odoo_Integration.action_monta_order_status",
            "Monta-Odoo-Integration.action_monta_order_status",
            "monta_odoo_integration.action_monta_order_status",
            "monta_module.action_monta_order_status",
        ]

        action_vals = None
        for xid in candidate_xmlids:
            try:
                action_vals = self.env.ref(xid, raise_if_not_found=True).sudo().read()[0]
                _logger.debug("Resolved Monta action via XMLID: %s", xid)
                break
            except ValueError:
                continue

        # If the XMLID couldn't be resolved, construct a safe fallback action
        if not action_vals:
            _logger.warning(
                "Could not resolve any Monta action XMLID. Using runtime fallback action."
            )
            action_vals = {
                "type": "ir.actions.act_window",
                "name": "Monta Order Status",
                "res_model": "monta.order.status",
                "view_mode": "tree,form",
                "target": "current",
            }

        # Ensure the action opens only the records of the current sale order
        action_vals["domain"] = [("sale_order_id", "=", self.id)]

        ctx = dict(self.env.context or {})
        ctx.update({"default_sale_order_id": self.id})
        action_vals["context"] = ctx

        return action_vals
