# -*- coding: utf-8 -*-
from odoo import fields, models


class EduSubscriptionWizard(models.TransientModel):
    _name = 'edu.subscription.wizard'
    _description = 'New Subscription Wizard'

    student_id = fields.Many2one('res.partner', required=True,
        domain=[('x_is_student','=',True)])
    type_id = fields.Many2one('edu.subscription.type', required=True)
    start_date = fields.Date(default=fields.Date.today)
    carried_over = fields.Integer(default=0, string='Carry Over Lessons')
    notes = fields.Text()

    def action_create(self):
        sub = self.env['edu.subscription'].create({
            'student_id': self.student_id.id,
            'type_id': self.type_id.id,
            'start_date': self.start_date,
            'lessons_remaining': self.type_id.lesson_count + self.carried_over,
            'carried_over_lessons': self.carried_over,
            'notes': self.notes,
        })
        source_id = self.env.context.get('source_subscription_id')
        if source_id:
            self.env['edu.subscription'].browse(source_id).write({
                'status': 'cancelled',
                'lessons_remaining': 0,
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'edu.subscription',
            'res_id': sub.id,
            'view_mode': 'form',
        }
