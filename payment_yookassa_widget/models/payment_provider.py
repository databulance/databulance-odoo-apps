# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('yookassa', 'YooKassa')],
        ondelete={'yookassa': 'set default'},
    )
    yookassa_shop_id = fields.Char(
        string="Shop ID",
        required_if_provider='yookassa',
    )
    yookassa_secret_key = fields.Char(
        string="Secret Key",
        required_if_provider='yookassa',
    )

    def _get_supported_features(self):
        res = super()._get_supported_features()
        if self.code == 'yookassa':
            res['support_inline_form'] = True
        return res
