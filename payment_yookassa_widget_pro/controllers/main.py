# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class YooKassaProController(http.Controller):

    # ── RETURN OVERRIDE ────────────────────────────────────────────
    # Overrides the free module's /return to trigger onboarding.

    @http.route(
        '/payment/yookassa/return',
        type='http', auth='public', methods=['GET', 'POST'],
        csrf=False, save_session=False,
    )
    def yookassa_return(self, **params):
        tx_ref = params.get('tx_ref')
        _logger.info("YooKassa Pro: return tx_ref=%s", tx_ref)

        if tx_ref:
            tx = request.env['payment.transaction'].sudo().search(
                [('reference', '=', tx_ref)], limit=1
            )
            if tx:
                tx._yookassa_get_status_sync()
            return request.redirect(
                f'/payment/yookassa/onboarding?tx_ref={tx_ref}'
            )
        return request.redirect('/payment/status')

    # ── ONBOARDING ROUTER ──────────────────────────────────────────

    @http.route(
        '/payment/yookassa/onboarding',
        type='http', auth='public', methods=['GET'],
        website=True,
    )
    def onboarding(self, tx_ref=None, **kwargs):
        if not tx_ref:
            return request.redirect('/payment/status')

        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_ref)], limit=1
        )
        if not tx:
            return request.redirect('/payment/status')

        if tx.state == 'draft':
            tx._yookassa_get_status_sync()

        if tx.state == 'cancel':
            return request.redirect('/payment/status')

        partner = tx.partner_id
        next_step = partner._yk_onboarding_next_step(tx_ref)

        # Auto-send verification email if that's the next step
        if next_step == (
            f'/payment/yookassa/verify-email?tx_ref={tx_ref}'
        ):
            base_url = request.env[
                'ir.config_parameter'
            ].sudo().get_param('web.base.url', '')
            partner.sudo()._yk_send_verification_email(
                base_url, tx_ref
            )

        return request.redirect(next_step)

    # ── EMAIL VERIFICATION ─────────────────────────────────────────

    @http.route(
        '/payment/yookassa/verify-email',
        type='http', auth='public', methods=['GET'],
        website=True,
    )
    def verify_email_page(
        self, tx_ref=None, resent=None, **kwargs
    ):
        tx = (
            request.env['payment.transaction'].sudo().search(
                [('reference', '=', tx_ref)], limit=1
            )
            if tx_ref else None
        )
        return request.render(
            'payment_yookassa_widget_pro.verify_email_page',
            {
                'tx_ref': tx_ref,
                'email': tx.partner_id.email if tx else '',
                'resent': resent == '1',
            },
        )

    @http.route(
        '/payment/yookassa/resend-verify',
        type='http', auth='public', methods=['GET'],
        website=True,
    )
    def resend_verify_email(self, tx_ref=None, **kwargs):
        if not tx_ref:
            return request.redirect('/payment/status')
        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_ref)], limit=1
        )
        if tx:
            base_url = request.env[
                'ir.config_parameter'
            ].sudo().get_param('web.base.url', '')
            tx.partner_id.sudo().x_email_verify_token = False
            tx.partner_id.sudo()._yk_send_verification_email(
                base_url, tx_ref
            )
        return request.redirect(
            f'/payment/yookassa/verify-email?tx_ref={tx_ref}&resent=1'
        )

    @http.route(
        '/payment/yookassa/confirm-email',
        type='http', auth='public', methods=['GET'],
        website=True,
    )
    def confirm_email(self, token=None, tx_ref=None, **kwargs):
        if not token or not tx_ref:
            return request.render(
                'payment_yookassa_widget_pro.email_confirm_error',
                {
                    'error': 'Invalid verification link.',
                    'tx_ref': tx_ref,
                },
            )
        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_ref)], limit=1
        )
        if not tx:
            return request.render(
                'payment_yookassa_widget_pro.email_confirm_error',
                {
                    'error': 'Transaction not found.',
                    'tx_ref': tx_ref,
                },
            )
        if tx.partner_id.sudo()._yk_confirm_email_token(token):
            return request.redirect(
                f'/payment/yookassa/onboarding?tx_ref={tx_ref}'
            )
        return request.render(
            'payment_yookassa_widget_pro.email_confirm_error',
            {
                'error': (
                    'Verification link is invalid or '
                    'has already been used.'
                ),
                'tx_ref': tx_ref,
            },
        )

    # ── PASSWORD SETUP ─────────────────────────────────────────────

    @http.route(
        '/payment/yookassa/set-password',
        type='http', auth='public', methods=['GET'],
        website=True,
    )
    def set_password_page(
        self, tx_ref=None, error=None, **kwargs
    ):
        if not tx_ref:
            return request.redirect('/payment/status')
        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_ref)], limit=1
        )
        if not tx:
            return request.redirect('/payment/status')
        partner = tx.partner_id
        existing = partner.sudo().user_ids.filtered(
            lambda u: u.active
        )[:1]
        if existing:
            partner.sudo().x_password_set = True
            return request.redirect(
                f'/payment/yookassa/onboarding?tx_ref={tx_ref}'
            )
        return request.render(
            'payment_yookassa_widget_pro.set_password_page',
            {
                'tx_ref': tx_ref,
                'partner_name': partner.name,
                'email': partner.email,
                'error': error,
            },
        )

    @http.route(
        '/payment/yookassa/set-password',
        type='http', auth='public', methods=['POST'],
        website=True, csrf=True,
    )
    def set_password_submit(
        self, tx_ref=None, password=None,
        password_confirm=None, **kwargs
    ):
        if not tx_ref:
            return request.redirect('/payment/status')
        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_ref)], limit=1
        )
        if not tx:
            return request.redirect('/payment/status')

        partner = tx.partner_id

        def _render_error(msg):
            return request.render(
                'payment_yookassa_widget_pro.set_password_page',
                {
                    'tx_ref': tx_ref,
                    'partner_name': partner.name,
                    'email': partner.email,
                    'error': msg,
                },
            )

        if not password or len(password) < 8:
            return _render_error(
                'Password must be at least 8 characters.'
            )
        if password != password_confirm:
            return _render_error('Passwords do not match.')

        try:
            portal_group = request.env.ref('base.group_portal')
            new_user = request.env['res.users'].sudo().create({
                'name': partner.name,
                'login': partner.email,
                'email': partner.email,
                'partner_id': partner.id,
                'group_ids': [(6, 0, [portal_group.id])],
            })
            new_user.sudo()._set_password(password)
            partner.sudo().x_password_set = True
        except Exception as exc:
            _logger.exception(
                "YooKassa Pro: portal user creation failed: %s", exc
            )
            return _render_error(
                'An account with this email already exists.'
            )

        try:
            uid = request.session.authenticate(
                request.env.cr.dbname, partner.email, password
            )
            if uid:
                request.session['uid'] = uid
        except Exception:
            pass

        return request.redirect(
            f'/payment/yookassa/onboarding?tx_ref={tx_ref}'
        )
