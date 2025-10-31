# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Flag orders that should be pushed by the cron
    monta_pending_push = fields.Boolean(default=False, copy=False, help="If enabled, cron will push this order to Monta.")

    @api.model
    def _cron_monta_pull_status(self, limit=200):
        """Cron: Pull Monta status for orders that already have a Monta reference."""
        domain = [('monta_order_ref', '!=', False)]
        orders = self.search(domain, limit=limit)
        pulled = 0
        for so in orders:
            try:
                # Prefer your existing methods/services; adjust names if different
                if hasattr(so, "_monta_sync_status_once"):
                    so.with_context(cron_run=True)._monta_sync_status_once()
                elif hasattr(so, "action_monta_sync_status"):
                    so.with_context(cron_run=True).action_monta_sync_status()
                else:
                    _logger.debug("No status sync method found on sale.order for %s", so.name)
                    continue
                pulled += 1
            except Exception:
                _logger.exception("Monta pull status failed for %s", so.name)
        _logger.info("Monta cron: pulled status for %s orders.", pulled)
        return True

    @api.model
    def _cron_monta_push_pending(self, limit=200):
        """Cron: Push orders that are flagged as pending to Monta."""
        domain = [('monta_pending_push', '=', True)]
        orders = self.search(domain, limit=limit)
        pushed = 0
        for so in orders:
            try:
                if hasattr(so, "action_push_to_monta"):
                    so.with_context(cron_run=True).action_push_to_monta()
                    so.monta_pending_push = False
                    pushed += 1
                else:
                    _logger.debug("No push method found on sale.order for %s", so.name)
            except Exception:
                _logger.exception("Monta push failed for %s", so.name)
        _logger.info("Monta cron: pushed %s pending orders.", pushed)
        return True

    @api.model
    def _cron_monta_sync_products_inbound(self):
        """Cron: Optional nightly product & inbound sync (wire to your services if you use them)."""
        done = False
        try:
            # Preferred: call service-layer functions if you have them
            try:
                from ..services.monta_products import sync_products_to_monta
                from ..services.monta_inbound import sync_inbound_forecasts
                sync_products_to_monta(self.env)
                sync_inbound_forecasts(self.env)
                done = True
            except Exception:
                # Fallback: call model-level actions if you expose them
                if hasattr(self, "action_monta_sync_products"):
                    self.action_monta_sync_products()
                    done = True
                if hasattr(self, "action_monta_sync_inbound"):
                    self.action_monta_sync_inbound()
                    done = True
        except Exception:
            _logger.exception("Monta nightly product/inbound sync failed.")
        if done:
            _logger.info("Monta cron: products/inbound sync completed.")
        return True
