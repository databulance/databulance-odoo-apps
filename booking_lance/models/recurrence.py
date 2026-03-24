from odoo import models, fields, api
from datetime import timedelta


class BookingLanceRecurrence(models.Model):
    _name = 'booking_lance.recurrence'
    _description = 'Booking Recurrence Rule'

    booking_id = fields.Many2one(
        'booking_lance.booking',
        string='Parent Booking',
        required=True,
        ondelete='cascade',
    )
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 2 Weeks'),
        ('monthly', 'Monthly'),
    ], string='Frequency', required=True, default='weekly')
    interval = fields.Integer(
        string='Repeat Every',
        default=1,
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
    )
    booking_ids = fields.One2many(
        'booking_lance.booking',
        'recurrence_id',
        string='Generated Bookings',
    )
    booking_count = fields.Integer(
        string='Bookings',
        compute='_compute_booking_count',
    )

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)

    def action_generate_recurring_bookings(self):
        self.ensure_one()
        parent = self.booking_id
        frequency_days = {
            'weekly': 7,
            'biweekly': 14,
            'monthly': 30,
        }
        delta = timedelta(days=frequency_days[self.frequency])
        next_date = parent.start_datetime + delta

        while next_date.date() <= self.end_date:
            matching_slot = self.env['booking_lance.slot'].search([
                ('staff_id', '=', parent.staff_id.id),
                ('service_id', '=', parent.service_id.id),
                ('start_datetime', '>=', next_date),
                ('start_datetime', '<=', next_date + timedelta(
                    hours=1
                )),
                ('state', '=', 'available'),
            ], limit=1)

            if matching_slot:
                new_booking = parent.copy({
                    'slot_id': matching_slot.id,
                    'recurrence_id': self.id,
                    'is_recurring': True,
                    'state': 'draft',
                    'name': 'New',
                })
                new_booking.action_confirm()

            next_date += delta
