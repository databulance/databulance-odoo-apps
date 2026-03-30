# -*- coding: utf-8 -*-
from odoo import fields, models, api


class EduStudent(models.Model):
    _inherit = 'res.partner'

    x_is_student = fields.Boolean(default=False, index=True, string='Is Student')
    x_level_id = fields.Many2one('edu.level', string='Level', ondelete='set null')
    x_subject_ids = fields.Many2many(
        'edu.subject', 'edu_student_subject_rel',
        'partner_id', 'subject_id', string='Subjects',
    )
    x_email_verified = fields.Boolean(default=False, copy=False, string='Email Verified')
    x_email_verify_token = fields.Char(copy=False, index=True)
    x_placement_test_done = fields.Boolean(default=False, string='Placement Done')
    x_portal_language = fields.Selection(
        [('en','English'),('ru','Russian')], default='en',
    )
    x_timezone = fields.Char(default='UTC', string='Student Timezone')
    subscription_ids = fields.One2many('edu.subscription','student_id')
    subscription_count = fields.Integer(compute='_compute_student_counts')
    active_subscription_id = fields.Many2one(
        'edu.subscription', compute='_compute_active_sub', store=False,
    )
    visit_count = fields.Integer(compute='_compute_student_counts')
    homework_count = fields.Integer(compute='_compute_student_counts')

    @api.depends('subscription_ids')
    def _compute_student_counts(self):
        for rec in self:
            rec.subscription_count = len(rec.subscription_ids)
            rec.visit_count = self.env['edu.visit'].search_count([
                ('student_id','=',rec.id)
            ])
            rec.homework_count = self.env['edu.submission'].search_count([
                ('student_id','=',rec.id)
            ])

    @api.depends('subscription_ids.status')
    def _compute_active_sub(self):
        for rec in self:
            active = rec.subscription_ids.filtered(
                lambda s: s.status == 'active'
            )
            rec.active_subscription_id = active[:1]
