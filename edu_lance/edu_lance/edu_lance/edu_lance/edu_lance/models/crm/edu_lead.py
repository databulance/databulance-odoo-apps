# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError


class EduLead(models.Model):
    _name = 'edu.lead'
    _description = 'Student Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'partner_name'

    partner_name = fields.Char(required=True, tracking=True)
    email = fields.Char(tracking=True)
    phone = fields.Char(tracking=True)
    partner_id = fields.Many2one('res.partner', ondelete='set null')
    stage_id = fields.Many2one(
        'edu.pipeline.stage', required=True, tracking=True,
        default=lambda s: s._default_stage(),
        group_expand='_expand_stages',
    )
    priority = fields.Selection(
        [('0','Normal'),('1','High'),('2','Very High')], default='0',
    )
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', default=lambda s: s.env.user, tracking=True,
    )
    subject_id = fields.Many2one('edu.subject')
    level_id = fields.Many2one('edu.level')
    source = fields.Selection(
        [('widget','Widget'),('manual','Manual'),('referral','Referral'),
         ('social','Social'),('website','Website'),('other','Other')],
        default='manual',
    )
    notes = fields.Html()
    trial_session_id = fields.Many2one('edu.session', ondelete='set null')
    trial_date = fields.Datetime(related='trial_session_id.date_start', store=True)
    converted_at = fields.Datetime(readonly=True, copy=False)
    converted_student_id = fields.Many2one('res.partner', readonly=True, copy=False)

    def _default_stage(self):
        return self.env['edu.pipeline.stage'].search([('code','=','new')], limit=1)

    def _expand_stages(self, stages, domain, order):
        return self.env['edu.pipeline.stage'].search([], order=order)

    def action_convert_to_student(self):
        self.ensure_one()
        if self.converted_student_id:
            raise UserError('Already converted.')
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = self.env['res.partner'].create({
                'name': self.partner_name,
                'email': self.email,
                'phone': self.phone,
                'x_is_student': True,
                'x_level_id': self.level_id.id if self.level_id else False,
                'x_subject_ids': [(4, self.subject_id.id)] if self.subject_id else [],
            })
        partner.write({'x_is_student': True})
        enrolled = self.env['edu.pipeline.stage'].search([('code','=','enrolled')], limit=1)
        self.write({
            'converted_at': fields.Datetime.now(),
            'converted_student_id': partner.id,
            'partner_id': partner.id,
            'stage_id': enrolled.id or self.stage_id.id,
        })
        # Open subscription wizard if model exists, else open student form
        if self.env['ir.model'].sudo().search([('model','=','edu.subscription.wizard')]):
            return {
                'type': 'ir.actions.act_window',
                'name': 'New Subscription',
                'res_model': 'edu.subscription.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_student_id': partner.id},
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
        }
