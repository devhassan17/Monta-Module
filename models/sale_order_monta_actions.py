# -*- coding: utf-8 -*-
import hashlib
import logging
from datetime import timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

def _hash_reason(reason: str) -> str:
    reason = (reason or "").strip()
    return hashlib.sha1(reason.encode("utf-8")).hexdigest() if reason else ""

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Minimal fields to throttle duplicate chatter notes
    monta_last_error_hash = fields.Char(copy=False, index=True)
    monta_last_error_at = fields.Datetime(copy=False)

    # ----------------------
    # One-note-on-failure API
    # ----------------------
    def _post_single_block_note(self, reason: str, *, ttl_hours=24):
        """Post ONLY ONE chatter note per (order, reason) within ttl_hours."""
        self.ensure_one()
        h = _hash_reason(reason)
        now = fields.Datetime.now()
        if self.monta_last_error_hash == h and self.monta_last_error_at and \
           (now - self.monta_last_error_at) < timedelta(hours=ttl_hours):
            # Already posted recently; do nothing
            return False

        body = (
            "<p><b>Monta</b>: Order <b>blocked</b>.</p>"
            f"<p><b>Reason:</b> {reason or 'Unknown'}</p>"
        )
        # Quiet internal note (no follower emails)
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
        """Call this on success so next failure can notify again."""
        self.write({
            "monta_last_error_hash": False,
            "monta_last_error_at": False,
        })

    # -----------------------------------------
    # Button: open Monta status (kept from before)
    # -----------------------------------------
    def action_open_monta_order_status(self):
        """Open Monta order status records for this Sale Order with robust XMLID resolution."""
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
                _logger.debug("Resolved Monta action via XMLID: %s", xid)
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

    # -------------------------------------------------------
    # Buttons: push/sync — fail fast & post ONE chatter note
    # -------------------------------------------------------
    def action_push_to_monta(self):
        """
        Wrap the original push with a guard:
        - On first failure: stop immediately, post ONE concise chatter message, log ONE warning.
        - On success: clear failure flags.
        """
        self.ensure_one()
        try:
            # Call original implementation if it exists
            # (If none exists elsewhere, raise AttributeError to inform)
            return super(SaleOrder, self).action_push_to_monta()
        except AttributeError:
            # No original method defined: treat as configuration error (one note)
            reason = "Push to Monta is not configured on this database."
            self._post_single_block_note(reason)
            _logger.warning("Monta push failed for %s: %s", self.name, reason)
            return False
        except Exception as e:
            # Fail fast, no heavy processing; one note + one log
            reason = str(e)
            self._post_single_block_note(reason)
            _logger.warning("Monta push failed for %s: %s", self.name, reason)
            return False
        else:
            # If no exception, clear flags
            self._clear_block_note_flags()

    def action_monta_sync_status(self):
        """
        Wrap the original status sync with the same guard behavior.
        """
        self.ensure_one()
        try:
            return super(SaleOrder, self).action_monta_sync_status()
        except AttributeError:
            reason = "Monta status sync is not configured on this database."
            self._post_single_block_note(reason)
            _logger.warning("Monta status sync failed for %s: %s", self.name, reason)
            return False
        except Exception as e:
            reason = str(e)
            self._post_single_block_note(reason)
            _logger.warning("Monta status sync failed for %s: %s", self.name, reason)
            return False
        else:
            self._clear_block_note_flags()
