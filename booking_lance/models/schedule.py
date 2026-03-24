from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BookingLanceSchedule(models.Model):
    _name = 'booking_lance.schedule'
    _description = 'Staff Weekly Schedule'
    _order = 'staff_id, day_of_week, time_from'

    staff_id = fields.Many2one(
        'booking_lance.staff',
        string='Staff Member',
        required=True,
        ondelete='cascade',
    )
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Day', required=True)
    time_from = fields.Float(
        string='From',
        required=True,
        default=9.0,
    )
    time_to = fields.Float(
        string='To',
        required=True,
        default=17.0,
    )
    active = fields.Boolean(default=True)

    @api.constrains('time_from', 'time_to')
    def _check_times(self):
        for rec in self:
            if rec.time_to <= rec.time_from:
                raise ValidationError(
                    'End time must be after start time.'
                )
            if rec.time_from < 0 or rec.time_to > 24:
                raise ValidationError(
                    'Times must be between 0 and 24.'
                )
