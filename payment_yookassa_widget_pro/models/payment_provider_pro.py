# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PaymentProviderPro(models.Model):
    _inherit = 'payment.provider'

    yookassa_pro_license_key = fields.Char(
        string="YooKassa Pro License Key",
        help="Purchase at https://databulance.com/yookassa-pro",
    )
    yookassa_pro_license_status = fields.Char(
        string="License Status",
        compute='_compute_license_status',
        store=False,
    )

    @api.depends('yookassa_pro_license_key', 'code')
    def _compute_license_status(self):
        for rec in self:
            if rec.code != 'yookassa':
                rec.yookassa_pro_license_status = ''
                continue
            # Sync key to ir.config_parameter for the validator
            if rec.yookassa_pro_license_key:
                self.env['ir.config_parameter'].sudo().set_param(
                    'yookassa_pro.license_key',
                    rec.yookassa_pro_license_key,
                )
            status_code, msg = self.env[
                'yookassa.pro.license'
            ].get_status_message()
            rec.yookassa_pro_license_status = msg
