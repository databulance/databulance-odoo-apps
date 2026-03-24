# -*- coding: utf-8 -*-
import logging
import requests
from datetime import datetime, timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)
LICENSE_ENDPOINT = "https://databulance.com/api/license/validate"
CACHE_PARAM = "yookassa_pro.license_valid_until"
CACHE_HOURS = 24


class LicenseValidator(models.AbstractModel):
    _name = 'yookassa.pro.license'
    _description = 'YooKassa Pro License Validator'

    @api.model
    def is_valid(self):
        """
        Returns True if the license is valid.
        Caches result for CACHE_HOURS to avoid hammering the endpoint.
        Fails open in offline/error scenarios — never blocks payments.
        """
        params = self.env['ir.config_parameter'].sudo()
        key = params.get_param('yookassa_pro.license_key', '')

        if not key:
            _logger.warning(
                "YooKassa Pro: no license key configured. "
                "Set in Settings → Technical → System Parameters "
                "→ yookassa_pro.license_key. "
                "Get a key at databulance.com"
            )
            # Fail open — never block functionality
            return True

        # Check cache
        valid_until_str = params.get_param(CACHE_PARAM, '')
        if valid_until_str:
            try:
                valid_until = datetime.fromisoformat(valid_until_str)
                if datetime.utcnow() < valid_until:
                    return True
            except ValueError:
                pass

        # Validate against license server
        try:
            db_uuid = params.get_param('database.uuid', '')
            resp = requests.post(
                LICENSE_ENDPOINT,
                json={
                    'key': key,
                    'module': 'payment_yookassa_widget_pro',
                    'db_uuid': db_uuid,
                },
                timeout=8,
            )
            if resp.status_code == 200 and resp.json().get('valid'):
                # Cache for 24 hours
                valid_until = (
                    datetime.utcnow() + timedelta(hours=CACHE_HOURS)
                ).isoformat()
                params.set_param(CACHE_PARAM, valid_until)
                _logger.info("YooKassa Pro: license valid — cached until %s",
                             valid_until)
                return True
            else:
                _logger.warning(
                    "YooKassa Pro: license invalid — response: %s",
                    resp.text[:200],
                )
                params.set_param(CACHE_PARAM, '')
                return False

        except requests.exceptions.ConnectionError:
            # Offline — fail open, don't block payments
            _logger.warning(
                "YooKassa Pro: license server unreachable — "
                "failing open to avoid blocking payments"
            )
            return True
        except Exception as exc:
            _logger.exception(
                "YooKassa Pro: license check error — %s", exc
            )
            return True  # fail open

    @api.model
    def get_status_message(self):
        """Returns a human-readable license status for the settings UI."""
        params = self.env['ir.config_parameter'].sudo()
        key = params.get_param('yookassa_pro.license_key', '')
        if not key:
            return ('no_key', 'No license key configured. '
                    'Purchase at databulance.com/yookassa-pro')
        if self.is_valid():
            valid_until = params.get_param(CACHE_PARAM, '')
            return ('valid', f'License active. Verified until: {valid_until[:16]}')
        return ('invalid', 'License invalid or expired. '
                'Contact support@databulance.com')
