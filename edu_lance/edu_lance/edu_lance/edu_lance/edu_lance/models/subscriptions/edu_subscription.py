# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import timedelta


class EduSubscriptionType(models.Model):
    _name = 'edu.subscription.type'
    _description = 'Subscription Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    lesson_count = fields.Integer(default=8, string='Lessons')
    validity_days = fields.Integer(default=30, string='Valid (days)')
    price = fields.Float(digits=(10,2))
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )
    subscription_mode = fields.Selection(
        [('per_lesson','Per Lesson'),('hourly','Hourly'),
         ('season','Season Pass')],
        default='per_lesson', required=True,
    )
    subject_ids = fields.Many2many('edu.subject')
    level_ids = fields.Many2many('edu.level')
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    color = fields.Integer(default=0)


class EduSubscription(models.Model):
    _name = 'edu.subscription'
    _description = 'Student Subscription'
    _inherit = ['mail.thread']
    _order = 'student_id, start_date desc'

    student_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade',
        domain=[('x_is_student','=',True)], index=True,
    )
    type_id = fields.Many2one(
        'edu.subscription.type', required=True, ondelete='restrict',
    )
    subscription_mode = fields.Selection(
        related='type_id.subscription_mode', store=True,
    )
    start_date = fields.Date(required=True, default=fields.Date.today)
    # FIX: expiry_date not required — auto-computed in create
    expiry_date = fields.Date()
    lessons_remaining = fields.Integer(default=0)
    status = fields.Selection(
        [('active','Active'),('expired','Expired'),
         ('exhausted','Exhausted'),('cancelled','Cancelled')],
        default='active', tracking=True,
    )
    # Plug-and-play: populated by payment_yookassa_widget when installed
    payment_tx_id = fields.Many2one(
        'payment.transaction', ondelete='set null', copy=False,
    )
    payment_state = fields.Selection(
        related='payment_tx_id.state', store=True, string='Payment Status',
    )
    carried_over_lessons = fields.Integer(default=0)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('type_id'):
                stype = self.env['edu.subscription.type'].browse(vals['type_id'])
                if 'lessons_remaining' not in vals:
                    vals['lessons_remaining'] = stype.lesson_count
                if not vals.get('expiry_date'):
                    start = fields.Date.from_string(
                        vals.get('start_date') or fields.Date.today()
                    )
                    vals['expiry_date'] = (
                        start + timedelta(days=stype.validity_days)
                    ).isoformat()
        return super().create(vals_list)

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_carry_over(self):
        self.ensure_one()
        if self.lessons_remaining <= 0:
            raise UserError('No lessons to carry over.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Subscription',
            'res_model': 'edu.subscription.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.student_id.id,
                'default_carried_over': self.lessons_remaining,
                'source_subscription_id': self.id,
            },
        }

    @api.model
    def _cron_check_expiry(self):
        today = fields.Date.today()
        self.search([
            ('status','=','active'),('expiry_date','<', today),
        ]).write({'status': 'expired'})
        self.search([
            ('status','=','active'),
            ('lessons_remaining','<=',0),
            ('subscription_mode','=','per_lesson'),
        ]).write({'status': 'exhausted'})
