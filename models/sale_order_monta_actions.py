# -*- coding: utf-8 -*-
import hashlib
import logging
from datetime import timedelta
from odoo import models, fields, api
from ..utils.log_silencer import silence_monta_logs

_logger = logging.getLogger(__name__)

def _hash_reason(reason: str) -> str:
    reason = (reason or "").strip()
    return hashlib.sha1(reason.encode("utf-8")).hexdigest() if reason else ""

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Minimal fields to throttle duplicate chatter notes
    monta_last_error_hash = fields.Char(copy=False, index=True)
    monta_last_error_at = fields.Datetime(copy=False)

    # -----------------------------------------
    # One-note-on-failure helpers
    # -----------------------------------------
    def _post_single_block_note(self, reason: str, *, ttl_hours=24):
        """Post ONLY ONE chatter note per (order, reason) within ttl_hours."""
        self.ensure_one()
        h = _hash_reason(reason)
        now = fields.Datetime.now()
        if self.monta_last_error_hash == h and self.monta_last_error_at and \
           (now - self.monta_last_error_at) < timedelta(hours=ttl_hours):
            return False

        body = (
            "<p><b>Monta</b>: Order <b>blocked</b>.</p>"
            f"<p><b>Reason:</b> {reason or 'Unknown'}</p>"
        )
        self.with_context(mail_post_autofollow=False).message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            notify=False,
        )
        self.write({
            "monta_last_error_hash": h,
            "monta_last_error_at": now,
        })
        return True

    def _clear_block_note_flags(self):
        self.write({
            "monta_last_error_hash": False,
            "monta_last_error_at": False,
        })

    # -----------------------------------------
    # Button: open Monta status (unchanged behavior)
    # -----------------------------------------
    def action_open_monta_order_status(self):
        self.ensure_one()
        candidate_xmlids = [
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
                break
            except ValueError:
                continue
        if not action_vals:
            action_vals = {
                "type": "ir.actions.act_window",
                "name": "Monta Order Status",
                "res_model": "monta.order.status",
                "view_mode": "list,form",
                "target": "current",
            }
        action_vals["domain"] = [("sale_order_id", "=", self.id)]
        ctx = dict(self.env.context or {})
        ctx.update({"default_sale_order_id": self.id})
        action_vals["context"] = ctx
        return action_vals

    # -----------------------------------------
    # Buttons wrapped with silence + single-note
    # -----------------------------------------
    def action_push_to_monta(self):
        """
        Fail fast, silence module logs inside, then post ONE note + ONE warning.
        """
        self.ensure_one()
        with silence_monta_logs():
            try:
                # Call the original implementation if defined upstream
                res = super(SaleOrder, self).action_push_to_monta()
                # Success => clear flags
                self._clear_block_note_flags()
                return res
            except AttributeError:
                reason = "Push to Monta is not configured."
                self._post_single_block_note(reason)
                _logger.warning("Monta push failed for %s: %s", self.name, reason)
                return False
            except Exception as e:
                reason = str(e)
                self._post_single_block_note(reason)
                _logger.warning("Monta push failed for %s: %s", self.name, reason)
                return False

    def action_monta_sync_status(self):
        """
        Same pattern for status sync.
        """
        self.ensure_one()
        with silence_monta_logs():
            try:
                res = super(SaleOrder, self).action_monta_sync_status()
                self._clear_block_note_flags()
                return res
            except AttributeError:
                reason = "Monta status sync is not configured."
                self._post_single_block_note(reason)
                _logger.warning("Monta status sync failed for %s: %s", self.name, reason)
                return False
            except Exception as e:
                reason = str(e)
                self._post_single_block_note(reason)
                _logger.warning("Monta status sync failed for %s: %s", self.name, reason)
                return False
