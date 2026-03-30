# -*- coding: utf-8 -*-
from odoo import fields, models


class EduLevel(models.Model):
    _name = 'edu.level'
    _description = 'Level'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    # code is optional — schools may use CEFR (A1-C2) or their own system
    code = fields.Char(
        string='Code',
        help='Optional short code e.g. A1, Beginner, Level 1. '
             'Leave blank if not applicable.',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    color = fields.Integer(default=0)
    # No UNIQUE constraint on code — allows custom levels + blank codes
