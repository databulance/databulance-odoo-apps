# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    edu_video_provider = fields.Selection(
        selection=[
            ('auto', 'Auto-detect'),
            ('bbb', 'BigBlueButton (nexus_vr)'),
            ('zoom', 'Zoom'),
            ('none', 'None — calendar only'),
        ],
        string='Video Provider', default='auto',
        config_parameter='edu_lance.video_provider',
    )
    edu_commission_rate = fields.Float(
        string='Default Commission (%)', default=20.0,
        config_parameter='edu_lance.commission_rate',
    )
    edu_auto_absent_minutes = fields.Integer(
        string='Auto-absent Grace (min)', default=45,
        config_parameter='edu_lance.auto_absent_minutes',
    )
    edu_writeoff_mode = fields.Selection(
        selection=[
            ('per_visit', 'Auto on attendance'),
            ('manual', 'Manual'),
        ],
        string='Write-off Mode', default='per_visit',
        config_parameter='edu_lance.writeoff_mode',
    )
    edu_portal_language = fields.Selection(
        selection=[('auto','Auto'),('en','English'),('ru','Russian')],
        string='Portal Language', default='auto',
        config_parameter='edu_lance.portal_language',
    )
    edu_enrollment_widget_enabled = fields.Boolean(
        string='Enable /enroll widget', default=True,
        config_parameter='edu_lance.enrollment_widget_enabled',
    )

    def _get_installed_bridges(self):
        IrModule = self.env['ir.module.module'].sudo()
        def installed(name):
            return bool(IrModule.search([
                ('name','=',name),('state','=','installed')
            ]))
        return {
            'yookassa': installed('payment_yookassa_widget'),
            'bbb': installed('nexus_vr'),
            'zoom': installed('nexus_zoom'),
        }
