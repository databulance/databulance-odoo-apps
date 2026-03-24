# -*- coding: utf-8 -*-
import uuid
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartnerPro(models.Model):
    _inherit = 'res.partner'

    x_placement_test_done = fields.Boolean(
        string="Placement Test Done",
        default=False,
    )
    x_email_verified = fields.Boolean(
        string="Email Verified",
        default=False,
        copy=False,
    )
    x_email_verify_token = fields.Char(
        string="Email Verification Token",
        copy=False,
        index=True,
    )
    x_password_set = fields.Boolean(
        string="Password Set via Onboarding",
        default=False,
        copy=False,
    )

    def _yk_onboarding_next_step(self, tx_ref):
        """
        Returns the URL for the next required onboarding step.
        Override this method to customize your post-payment flow.
        """
        self.ensure_one()

        if not self.x_email_verified:
            return (
                f'/payment/yookassa/verify-email?tx_ref={tx_ref}'
            )

        portal_user = self.user_ids.filtered(
            lambda u: u.active and u.share
        )[:1]
        if not portal_user and not self.x_password_set:
            return (
                f'/payment/yookassa/set-password?tx_ref={tx_ref}'
            )

        return '/payment/status'

    def _yk_send_verification_email(self, base_url, tx_ref):
        self.ensure_one()
        if not self.email:
            _logger.warning(
                "YooKassa Pro: partner %s has no email", self.id
            )
            return False

        token = (
            self.x_email_verify_token
            or str(uuid.uuid4()).replace('-', '')
        )
        self.sudo().x_email_verify_token = token

        verify_url = (
            f"{base_url}/payment/yookassa/confirm-email"
            f"?token={token}&tx_ref={tx_ref}"
        )

        mail_server = self.env['ir.mail_server'].sudo().search(
            [], limit=1
        )
        from_email = (
            mail_server.smtp_user
            if mail_server
            else 'noreply@example.com'
        )

        body_html = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;">
  <h2 style="color:#333;">Confirm your email address</h2>
  <p>Thank you for your purchase! Please verify your email to continue.</p>
  <p style="margin:28px 0;">
    <a href="{verify_url}"
       style="background:#875A7B;color:#fff;padding:12px 24px;
              text-decoration:none;border-radius:4px;font-size:16px;">
      Verify Email
    </a>
  </p>
  <p style="font-size:13px;color:#666;">
    Or copy this link: <a href="{verify_url}">{verify_url}</a>
  </p>
  <p style="font-size:12px;color:#999;margin-top:24px;">
    If you did not make this purchase, please ignore this email.
  </p>
</div>
"""
        mail = self.env['mail.mail'].sudo().create({
            'subject': 'Verify your email',
            'email_to': self.email,
            'email_from': from_email,
            'body_html': body_html,
            'auto_delete': True,
            'state': 'outgoing',
        })
        mail.send()
        _logger.info(
            "YooKassa Pro: verification email sent to %s", self.email
        )
        return True

    def _yk_confirm_email_token(self, token):
        self.ensure_one()
        if (self.x_email_verify_token
                and self.x_email_verify_token == token):
            self.sudo().write({
                'x_email_verified': True,
                'x_email_verify_token': False,
            })
            return True
        return False
