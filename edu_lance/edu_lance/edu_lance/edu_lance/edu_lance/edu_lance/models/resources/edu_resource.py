# -*- coding: utf-8 -*-
from odoo import fields, models


class EduResourceCategory(models.Model):
    _name = 'edu.resource.category'
    _description = 'Resource Category'
    _order = 'subject_id, sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    subject_id = fields.Many2one('edu.subject', ondelete='set null')
    level_id = fields.Many2one('edu.level', ondelete='set null')
    active = fields.Boolean(default=True)
    resource_ids = fields.One2many('edu.resource','category_id')
    resource_count = fields.Integer(compute='_compute_count')

    def _compute_count(self):
        for rec in self:
            rec.resource_count = len(rec.resource_ids)


class EduResource(models.Model):
    _name = 'edu.resource'
    _description = 'Teaching Resource'
    _inherit = ['mail.thread']
    _order = 'category_id, sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one('edu.resource.category', ondelete='set null')
    subject_id = fields.Many2one('edu.subject', ondelete='set null')
    level_id = fields.Many2one('edu.level', ondelete='set null')
    resource_type = fields.Selection(
        [('file','File'),('video','Video'),
         ('link','External Link'),('document','Document')],
        default='file', required=True,
    )
    url = fields.Char()
    file_id = fields.Many2one('ir.attachment', ondelete='set null')
    description = fields.Text(translate=True)
    tags = fields.Char()
    access = fields.Selection(
        [('public','All Students'),
         ('enrolled','Enrolled Only'),('teacher','Teachers Only')],
        default='enrolled',
    )
    active = fields.Boolean(default=True)
    source_resource_id = fields.Integer(readonly=True)
