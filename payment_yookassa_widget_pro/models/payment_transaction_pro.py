# -*- coding: utf-8 -*-
import uuid
import logging
import requests
from datetime import timedelta
from requests.auth import HTTPBasicAuth

from odoo import models, fields, api

_logger = logging.getLogger(__name__)
YOOKASSA_API = "https://api.yookassa.ru/v3"


class PaymentTransactionPro(models.Model):
    _inherit = 'payment.transaction'

    yk_completion_receipt_sent = fields.Boolean(
        string="54-ФЗ Receipt Sent",
        default=False, copy=False, index=True,
    )
    yk_completion_receipt_date = fields.Datetime(
        string="54-ФЗ Receipt Date",
        copy=False,
    )

    # ── 54-ФЗ COMPLETION RECEIPT ───────────────────────────────────

    def send_yookassa_completion_receipt(self):
        """
        Send a 54-ФЗ completion receipt for each eligible transaction.
        Called manually or via cron after service delivery.
        """
        if not self.env['yookassa.pro.license'].is_valid():
            _logger.warning(
                "YooKassa Pro: completion receipt blocked — invalid license"
            )
            return

        for tx in self:
            if tx.provider_code != 'yookassa':
                continue
            if tx.yk_completion_receipt_sent or not tx.provider_reference:
                continue
            tx._yookassa_create_completion_receipt()

    def _yookassa_create_completion_receipt(self):
        self.ensure_one()
        provider = self.provider_id
        auth = HTTPBasicAuth(
            provider.yookassa_shop_id,
            provider.yookassa_secret_key,
        )

        order = self.sale_order_ids[:1]
        items = []

        if order:
            for line in order.order_line.filtered(
                lambda l: not l.display_type
            ):
                items.append({
                    "description": line.name[:128],
                    "quantity": f"{float(line.product_uom_qty):.3f}",
                    "amount": {
                        "value": f"{float(line.price_unit):.2f}",
                        "currency": "RUB",
                    },
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                })
        else:
            items.append({
                "description": (
                    f"Educational services ({self.reference})"
                ),
                "quantity": "1.000",
                "amount": {
                    "value": f"{self.amount:.2f}",
                    "currency": "RUB",
                },
                "vat_code": 1,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            })

        payload = {
            "type": "payment",
            "send": True,
            "payment_id": self.provider_reference,
            "customer": {
                "email": (
                    self.partner_email
                    or self.partner_id.email
                    or "customer@example.com"
                )
            },
            "items": items,
            "settlements": [{
                "type": "prepayment",
                "amount": {
                    "value": f"{self.amount:.2f}",
                    "currency": "RUB",
                },
            }],
        }

        try:
            resp = requests.post(
                f"{YOOKASSA_API}/receipts",
                json=payload,
                auth=auth,
                headers={
                    "Idempotence-Key": str(uuid.uuid4()),
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            self.write({
                'yk_completion_receipt_sent': True,
                'yk_completion_receipt_date': fields.Datetime.now(),
            })
            _logger.info(
                "YooKassa Pro: 54-ФЗ receipt sent tx=%s", self.reference
            )
        except Exception:
            _logger.exception(
                "YooKassa Pro: FAILED 54-ФЗ receipt tx=%s", self.reference
            )


class PaymentTransactionProCron(models.AbstractModel):
    _name = 'payment.yookassa.pro.cron'
    _description = 'YooKassa Pro Cron Jobs'

    @api.model
    def cron_send_overdue_completion_receipts(self):
        """
        Send 54-ФЗ completion receipts for transactions where
        first_lesson_date was more than 45 days ago.
        Adjust the domain to match your service delivery model.
        """
        if not self.env['yookassa.pro.license'].is_valid():
            return

        cutoff = fields.Datetime.now() - timedelta(days=45)
        txs = self.env['payment.transaction'].search([
            ('provider_code', '=', 'yookassa'),
            ('state', '=', 'done'),
            ('yk_completion_receipt_sent', '=', False),
        ])
        # Filter further if sale order has a delivery/lesson date field
        eligible = txs.filtered(
            lambda t: t.sale_order_ids
            and any(
                getattr(o, 'first_lesson_date', False)
                and o.first_lesson_date <= cutoff
                for o in t.sale_order_ids
            )
        )
        _logger.info(
            "YooKassa Pro cron: %d transactions eligible for 54-ФЗ receipt",
            len(eligible),
        )
        eligible.send_yookassa_completion_receipt()
