from odoo import models, fields


class BookingLanceWebhook(models.Model):
    _name = 'booking_lance.webhook'
    _description = 'BookingLance Webhook Endpoint'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='Endpoint URL', required=True)
    event = fields.Selection([
        ('all', 'All Events'),
        ('confirmed', 'Booking Confirmed'),
        ('cancelled', 'Booking Cancelled'),
        ('rescheduled', 'Booking Rescheduled'),
        ('done', 'Session Done'),
    ], string='Trigger Event', required=True, default='all')
    secret_key = fields.Char(
        string='Secret Key',
        help='Sent as X-BookingLance-Secret header for verification.',
    )
    active = fields.Boolean(default=True)
    last_triggered = fields.Datetime(string='Last Triggered', readonly=True)
