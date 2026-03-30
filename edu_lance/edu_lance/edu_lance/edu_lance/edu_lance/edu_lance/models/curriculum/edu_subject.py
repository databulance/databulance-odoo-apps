# -*- coding: utf-8 -*-
from odoo import fields, models


class EduSubject(models.Model):
    _name = 'edu.subject'
    _description = 'Subject'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    icon = fields.Char(default='fa-book')
    curriculum_ids = fields.One2many('edu.curriculum','subject_id')
    curriculum_count = fields.Integer(compute='_compute_counts')
    student_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for rec in self:
            rec.curriculum_count = len(rec.curriculum_ids)
            rec.student_count = self.env['res.partner'].search_count([
                ('x_subject_ids','in', rec.id),
                ('x_is_student','=', True),
            ])
