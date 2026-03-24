# -*- coding: utf-8 -*-
import uuid
import decimal
import logging
import requests

from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
YOOKASSA_API = "https://api.yookassa.ru/v3"


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # ── RENDERING ──────────────────────────────────────────────────

    def _get_specific_rendering_values(self, processing_values):
        if self.provider_code != 'yookassa':
            return super()._get_specific_rendering_values(processing_values)

        self.ensure_one()
        _logger.info("YooKassa Widget: initialising payment tx=%s", self.reference)

        payment_data = self._yookassa_create_payment()
        token = payment_data.get('confirmation', {}).get('confirmation_token')

        if not token:
            _logger.error(
                "YooKassa Widget: no token tx=%s response=%s",
                self.reference, payment_data,
            )
            raise ValidationError(
                "YooKassa: Could not initialise payment. Please try again."
            )

        base_url = self.provider_id.get_base_url()
        return_url = (
            f"{base_url}/payment/yookassa/return?tx_ref={self.reference}"
        )
        checkout_url = f"{base_url}/payment/yookassa/checkout"

        _logger.info("YooKassa Widget: token obtained tx=%s", self.reference)
        return {
            'confirmation_token': token,
            'return_url': return_url,
            'tx_ref': self.reference,
            'checkout_url': checkout_url,
        }

    # ── PAYMENT CREATION ───────────────────────────────────────────

    def _yookassa_create_payment(self):
        self.ensure_one()
        provider = self.provider_id

        # Reuse an existing pending payment if available
        if self.provider_reference:
            try:
                resp = requests.get(
                    f"{YOOKASSA_API}/payments/{self.provider_reference}",
                    auth=(provider.yookassa_shop_id, provider.yookassa_secret_key),
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                if (data.get('status') == 'pending'
                        and data.get('confirmation', {}).get('confirmation_token')):
                    _logger.info(
                        "YooKassa: reusing pending payment %s",
                        self.provider_reference,
                    )
                    return data
            except Exception as exc:
                _logger.warning(
                    "YooKassa: could not fetch existing payment: %s", exc
                )

        amount = decimal.Decimal(str(self.amount)).quantize(
            decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP,
        )
        payload = {
            "amount": {
                "value": str(amount),
                "currency": self.currency_id.name or 'RUB',
            },
            "confirmation": {"type": "embedded"},
            "capture": True,
            "description": f"Order {self.reference}",
            "metadata": {
                "transaction_id": self.id,
                "reference": self.reference,
            },
        }

        receipt = self._yookassa_build_receipt()
        if receipt:
            payload["receipt"] = receipt

        try:
            resp = requests.post(
                f"{YOOKASSA_API}/payments",
                json=payload,
                auth=(provider.yookassa_shop_id, provider.yookassa_secret_key),
                headers={
                    "Idempotence-Key": str(uuid.uuid4()),
                    "Content-Type": "application/json",
                },
                timeout=20,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            _logger.exception(
                "YooKassa: API error tx=%s: %s", self.reference, exc
            )
            raise ValidationError(
                f"YooKassa payment creation failed: {exc}"
            ) from exc

        data = resp.json()
        self.provider_reference = data.get('id')
        _logger.info(
            "YooKassa: created id=%s status=%s tx=%s",
            self.provider_reference, data.get('status'), self.reference,
        )
        return data

    # ── BASIC RECEIPT ──────────────────────────────────────────────
    # Required by YooKassa when the merchant has fiscalisation enabled.
    # Pro module overrides this with full 54-ФЗ logic.

    def _yookassa_build_receipt(self):
        email = self.partner_email or self.partner_id.email
        if not email:
            _logger.warning(
                "YooKassa: no email for tx=%s — receipt omitted",
                self.reference,
            )
            return None

        order = self.sale_order_ids[:1]
        if not order:
            return {
                "customer": {"email": email},
                "items": [{
                    "description": f"Order {self.reference}",
                    "quantity": "1.000",
                    "amount": {
                        "value": f"{self.amount:.2f}",
                        "currency": self.currency_id.name or 'RUB',
                    },
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "service",
                }],
            }

        items = []
        for line in order.order_line.filtered(lambda l: not l.display_type):
            tax_rate = line.tax_ids[0].amount if line.tax_ids else 0
            vat_code = (
                4 if tax_rate == 20
                else 3 if tax_rate == 10
                else 1
            )
            items.append({
                "description": line.name[:128],
                "quantity": f"{float(line.product_uom_qty):.3f}",
                "amount": {
                    "value": f"{float(line.price_unit):.2f}",
                    "currency": "RUB",
                },
                "vat_code": vat_code,
                "payment_mode": "full_prepayment",
                "payment_subject": (
                    "service"
                    if line.product_id.type == "service"
                    else "commodity"
                ),
            })
        return {"customer": {"email": email}, "items": items} if items else None

    # ── STATUS SYNC ────────────────────────────────────────────────

    def _yookassa_get_status_sync(self):
        self.ensure_one()
        if not self.provider_reference:
            return
        provider = self.provider_id
        try:
            resp = requests.get(
                f"{YOOKASSA_API}/payments/{self.provider_reference}",
                auth=(provider.yookassa_shop_id, provider.yookassa_secret_key),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            _logger.info(
                "YooKassa: synced tx=%s status=%s",
                self.reference, data.get('status'),
            )
            self._process_notification_data({'object': data})
        except Exception as exc:
            _logger.exception(
                "YooKassa: sync failed tx=%s: %s", self.reference, exc
            )

    # ── NOTIFICATION PROCESSING ────────────────────────────────────

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        if provider_code != 'yookassa':
            return super()._get_tx_from_notification_data(
                provider_code, notification_data
            )

        event_data = notification_data.get('object', {})

        tx_ref = event_data.get('metadata', {}).get('reference')
        if tx_ref:
            return self.env['payment.transaction'].search(
                [('reference', '=', tx_ref),
                 ('provider_code', '=', 'yookassa')],
                limit=1,
            )

        yookassa_id = event_data.get('id')
        if yookassa_id:
            return self.env['payment.transaction'].search(
                [('provider_reference', '=', yookassa_id)],
                limit=1,
            )

        return self.env['payment.transaction']

    def _process_notification_data(self, notification_data):
        if self.provider_code != 'yookassa':
            return super()._process_notification_data(notification_data)

        status = notification_data.get('object', {}).get('status')
        _logger.info(
            "YooKassa: notification tx=%s status=%s",
            self.reference, status,
        )
        if status == 'succeeded':
            self._set_done()
        elif status in ('canceled', 'failed'):
            self._set_canceled()
        elif status == 'waiting_for_capture':
            self._set_pending()
