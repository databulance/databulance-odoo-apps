# -*- coding: utf-8 -*-
from odoo import fields, models, api


class EduHomework(models.Model):
    _name = 'edu.homework'
    _description = 'Homework'
    _inherit = ['mail.thread']
    _order = 'due_date, group_id'

    name = fields.Char(required=True, tracking=True)
    group_id = fields.Many2one('edu.group', required=True, ondelete='cascade')
    session_id = fields.Many2one('edu.session', ondelete='set null')
    description = fields.Html()
    due_date = fields.Datetime(required=True)
    attachment_ids = fields.Many2many('ir.attachment')
    submission_ids = fields.One2many('edu.submission','homework_id')
    submission_count = fields.Integer(compute='_compute_counts')
    pending_count = fields.Integer(compute='_compute_counts')
    active = fields.Boolean(default=True)

    @api.depends('submission_ids','submission_ids.grade')
    def _compute_counts(self):
        for rec in self:
            rec.submission_count = len(rec.submission_ids)
            rec.pending_count = sum(1 for s in rec.submission_ids if not s.grade)


class EduSubmission(models.Model):
    _name = 'edu.submission'
    _description = 'Homework Submission'
    _order = 'homework_id, student_id'

    homework_id = fields.Many2one('edu.homework', required=True, ondelete='cascade', index=True)
    student_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade', index=True,
        domain=[('x_is_student','=',True)],
    )
    submitted_at = fields.Datetime(default=fields.Datetime.now)
    text = fields.Html()
    file_ids = fields.Many2many('ir.attachment')
    grade = fields.Selection(
        [('A','A — Excellent'),('B','B — Good'),('C','C — Satisfactory'),
         ('D','D — Needs Improvement'),('F','F — Fail')],
    )
    feedback = fields.Text()
    graded_at = fields.Datetime(readonly=True)
    graded_by = fields.Many2one('res.users', readonly=True)

    _sql_constraints = [
        ('submission_uniq','UNIQUE(homework_id, student_id)',
         'Student already submitted this homework.'),
    ]

    def write(self, vals):
        if vals.get('grade'):
            vals['graded_at'] = fields.Datetime.now()
            vals['graded_by'] = self.env.uid
        return super().write(vals)
