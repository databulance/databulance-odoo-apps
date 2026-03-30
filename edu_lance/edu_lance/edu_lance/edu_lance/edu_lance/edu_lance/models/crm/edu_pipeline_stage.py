# -*- coding: utf-8 -*-
from odoo import fields, models


class EduPipelineStage(models.Model):
    _name = 'edu.pipeline.stage'
    _description = 'CRM Pipeline Stage'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    code = fields.Selection(
        selection=[
            ('new','New Inquiry'),('trial_scheduled','Trial Scheduled'),
            ('trial_done','Trial Done'),('enrolled','Enrolled'),
            ('active','Active'),('churned','Churned'),
        ],
    )
    fold = fields.Boolean(default=False)
    color = fields.Integer(default=0)
    requirements = fields.Text()
