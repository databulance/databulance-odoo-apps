from odoo import models, fields


class BookingLanceConfig(models.Model):
    _name = 'booking_lance.config'
    _description = 'BookingLance Configuration'
    _rec_name = 'website_id'

    website_id = fields.Many2one(
        'website',
        string='Website',
        required=True,
        ondelete='cascade',
    )
    brand_name = fields.Char(
        string='Brand Name',
        default='BookingLance',
        translate=True,
    )
    brand_color = fields.Char(
        string='Brand Color (hex)',
        default='#9c27b0',
    )
    brand_logo = fields.Binary(string='Brand Logo')
    brand_logo_filename = fields.Char(string='Logo Filename')
    confirmation_message = fields.Html(
        string='Booking Confirmation Message',
        translate=True,
        default='<p>Thank you for your booking. '
                'We will be in touch shortly.</p>',
    )
    cancellation_hours_limit = fields.Integer(
        string='Cancellation Deadline (hours)',
        default=24,
        help='Clients cannot cancel within this many hours of the session.',
    )
    reschedule_hours_limit = fields.Integer(
        string='Reschedule Deadline (hours)',
        default=24,
        help='Clients cannot reschedule within this many hours of the session.',
    )
    allow_waitlist = fields.Boolean(
        string='Enable Waitlist',
        default=True,
    )
    allow_recurring = fields.Boolean(
        string='Enable Recurring Bookings',
        default=True,
    )
    slot_generation_days = fields.Integer(
        string='Slot Generation Window (days)',
        default=30,
        help='How many days ahead to auto-generate available slots.',
    )
    notify_admin_email = fields.Char(
        string='Admin Notification Email',
        help='Email address to notify on new bookings.',
    )
    active = fields.Boolean(default=True)
