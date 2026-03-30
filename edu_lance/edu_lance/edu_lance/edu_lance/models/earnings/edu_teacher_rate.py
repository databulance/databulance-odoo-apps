# -*- coding: utf-8 -*-
from odoo import fields, models, api


class EduTeacherRate(models.Model):
    _name = 'edu.teacher.rate'
    _description = 'Teacher Rate Card'
    _order = 'teacher_id, subject_id'

    teacher_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade',
        domain=[('x_is_teacher','=',True)],
    )
    subject_id = fields.Many2one('edu.subject', ondelete='set null')
    level_id = fields.Many2one('edu.level', ondelete='set null')
    rate_type = fields.Selection(
        [('per_session','Per Session'),('per_hour','Per Hour'),
         ('per_student','Per Student')],
        default='per_session', required=True,
    )
    amount = fields.Float(required=True, digits=(10,2))
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )
    active = fields.Boolean(default=True)

    def _compute_amount(self, session):
        self.ensure_one()
        if self.rate_type == 'per_session':
            return self.amount
        elif self.rate_type == 'per_hour':
            return self.amount * (session.duration or 0)
        elif self.rate_type == 'per_student':
            present = sum(
                1 for v in session.visit_ids
                if v.status in ('present','late')
            )
            return self.amount * present
        return 0.0


class EduTeacherEarning(models.Model):
    _name = 'edu.teacher.earning'
    _description = 'Teacher Earning'
    _order = 'session_id desc'

    session_id = fields.Many2one('edu.session', required=True, ondelete='cascade', index=True)
    teacher_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True)
    rate_id = fields.Many2one('edu.teacher.rate', ondelete='set null')
    amount = fields.Float(digits=(10,2))
    commission_rate = fields.Float(digits=(5,2))
    # FIX: computed fields — do NOT set in create dict
    commission_amount = fields.Float(compute='_compute_net', store=True)
    net_amount = fields.Float(compute='_compute_net', store=True)
    payout_id = fields.Many2one('edu.payout', ondelete='set null')
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )

    @api.depends('amount','commission_rate')
    def _compute_net(self):
        for rec in self:
            rec.commission_amount = rec.amount * rec.commission_rate / 100
            rec.net_amount = rec.amount - rec.commission_amount


class EduPayout(models.Model):
    _name = 'edu.payout'
    _description = 'Teacher Payout'
    _inherit = ['mail.thread']
    _order = 'date_from desc'

    name = fields.Char(
        default=lambda s: s.env['ir.sequence'].next_by_code('edu.payout'),
    )
    teacher_id = fields.Many2one(
        'hr.employee', required=True, ondelete='restrict',
        domain=[('x_is_teacher','=',True)],
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    earning_ids = fields.One2many('edu.teacher.earning','payout_id')
    total_gross = fields.Float(compute='_compute_totals', store=True)
    total_commission = fields.Float(compute='_compute_totals', store=True)
    total_net = fields.Float(compute='_compute_totals', store=True)
    status = fields.Selection(
        [('draft','Draft'),('confirmed','Confirmed'),('paid','Paid')],
        default='draft', tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )
    notes = fields.Text()

    @api.depends('earning_ids.amount','earning_ids.commission_amount','earning_ids.net_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_gross = sum(rec.earning_ids.mapped('amount'))
            rec.total_commission = sum(rec.earning_ids.mapped('commission_amount'))
            rec.total_net = sum(rec.earning_ids.mapped('net_amount'))

    def action_confirm(self):
        self.write({'status': 'confirmed'})

    def action_mark_paid(self):
        self.write({'status': 'paid'})
