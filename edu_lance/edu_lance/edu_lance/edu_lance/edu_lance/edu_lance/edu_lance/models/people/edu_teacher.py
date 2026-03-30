# -*- coding: utf-8 -*-
from odoo import fields, models, api


class EduTeacher(models.Model):
    _inherit = 'hr.employee'

    x_is_teacher = fields.Boolean(default=False, index=True, string='Is Teacher')
    x_subject_ids = fields.Many2many(
        'edu.subject', 'edu_teacher_subject_rel',
        'employee_id', 'subject_id', string='Subjects',
    )
    x_level_ids = fields.Many2many(
        'edu.level', 'edu_teacher_level_rel',
        'employee_id', 'level_id', string='Levels',
    )
    x_bio = fields.Html(translate=True)
    x_bbb_user_id = fields.Char(copy=False, string='BBB User ID')
    x_zoom_user_id = fields.Char(copy=False, string='Zoom User ID')
    rate_ids = fields.One2many('edu.teacher.rate','teacher_id', string='Rates')
    earning_ids = fields.One2many('edu.teacher.earning','teacher_id')
    group_ids = fields.One2many('edu.group','teacher_id')
    group_count = fields.Integer(compute='_compute_teacher_counts')
    session_count = fields.Integer(compute='_compute_teacher_counts')

    @api.depends('group_ids')
    def _compute_teacher_counts(self):
        for rec in self:
            rec.group_count = len(rec.group_ids)
            rec.session_count = self.env['edu.session'].search_count([
                ('teacher_id','=',rec.id)
            ])
