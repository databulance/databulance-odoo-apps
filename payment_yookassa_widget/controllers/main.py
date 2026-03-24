# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class YooKassaWidgetController(http.Controller):

    # ── WEBHOOK ────────────────────────────────────────────────────

    @http.route(
        '/payment/yookassa/webhook',
        type='http', auth='public', methods=['POST'],
        csrf=False, save_session=False,
    )
    def yookassa_webhook(self):
        try:
            data = json.loads(
                request.httprequest.data.decode('utf-8')
            )
        except (ValueError, UnicodeDecodeError) as exc:
            _logger.error("YooKassa Webhook: Invalid JSON — %s", exc)
            return request.make_response("Invalid JSON", status=400)

        _logger.info(
            "YooKassa Webhook: event=%s payment=%s",
            data.get('event'),
            data.get('object', {}).get('id'),
        )

        tx = request.env['payment.transaction'].sudo()\
            ._get_tx_from_notification_data('yookassa', data)

        if tx and tx.exists():
            tx._process_notification_data(data)
            return request.make_response("OK", status=200)

        _logger.warning(
            "YooKassa Webhook: No transaction for payment_id=%s",
            data.get('object', {}).get('id'),
        )
        return request.make_response("Transaction Not Found", status=404)

    # ── CHECKOUT PAGE ──────────────────────────────────────────────

    @http.route(
        '/payment/yookassa/checkout',
        type='http', auth='public', methods=['GET'],
        website=True, sitemap=False,
    )
    def checkout_page(
        self, token=None, tx_ref=None, return_url=None, **kwargs
    ):
        if not token:
            _logger.warning("YooKassa checkout: no token in request")
            return request.redirect('/payment/status')

        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', ''
        )
        if not return_url:
            return_url = (
                f"{base_url}/payment/yookassa/return"
                f"?tx_ref={tx_ref or ''}"
            )

        _logger.info(
            "YooKassa checkout: rendering widget page tx=%s", tx_ref
        )
        return request.render(
            'payment_yookassa_widget.checkout_page',
            {
                'token': token,
                'tx_ref': tx_ref or '',
                'return_url': return_url,
            },
        )

    # ── RETURN ─────────────────────────────────────────────────────

    @http.route(
        '/payment/yookassa/return',
        type='http', auth='public', methods=['GET', 'POST'],
        csrf=False, save_session=False,
    )
    def yookassa_return(self, **params):
        _logger.info("YooKassa: User returned with params: %s", params)
        tx_ref = params.get('tx_ref')

        if tx_ref:
            tx = request.env['payment.transaction'].sudo().search(
                [('reference', '=', tx_ref)], limit=1
            )
            if tx:
                tx._yookassa_get_status_sync()
            return request.redirect('/payment/status')

        return request.redirect('/payment/status')
