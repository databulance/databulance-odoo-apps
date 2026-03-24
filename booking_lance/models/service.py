from odoo import models, fields, api


class BookingLanceService(models.Model):
    _name = 'booking_lance.service'
    _description = 'Bookable Service'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Service Name',
        required=True,
        translate=True,
        tracking=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Html(
        string='Description',
        translate=True,
    )
    image = fields.Binary(string='Image')
    image_filename = fields.Char(string='Image Filename')
    duration = fields.Float(
        string='Duration (hours)',
        required=True,
        default=1.0,
        tracking=True,
    )
    buffer_time = fields.Float(
        string='Buffer Time (hours)',
        default=0.0,
        help='Gap added after each session before the next slot is available.',
    )
    max_capacity = fields.Integer(
        string='Max Clients per Slot',
        default=1,
        help='Set above 1 for group sessions.',
    )
    cancellation_hours = fields.Integer(
        string='Cancellation Deadline (hours)',
        default=24,
        help='Override company default. 0 = use company setting.',
    )
    reschedule_hours = fields.Integer(
        string='Reschedule Deadline (hours)',
        default=24,
        help='Override company default. 0 = use company setting.',
    )
    allow_recurring = fields.Boolean(
        string='Allow Recurring',
        default=False,
    )
    allow_waitlist = fields.Boolean(
        string='Allow Waitlist',
        default=True,
    )
    payment_mode = fields.Selection([
        ('free', 'Free'),
        ('pay_at_session', 'Pay at Session'),
    ], string='Payment Mode', default='free', required=True)
    website_ids = fields.Many2many(
        'website',
        string='Available On Websites',
    )
    staff_ids = fields.Many2many(
        'booking_lance.staff',
        'booking_lance_service_staff_rel',
        'service_id',
        'staff_id',
        string='Assigned Staff',
    )
    category_id = fields.Many2one(
        'booking_lance.service.category',
        string='Category',
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    booking_ids = fields.One2many(
        'booking_lance.booking',
        'service_id',
        string='Bookings',
    )
    booking_count = fields.Integer(
        string='Total Bookings',
        compute='_compute_booking_count',
    )
    slot_ids = fields.One2many(
        'booking_lance.slot',
        'service_id',
        string='Slots',
    )
    slot_count = fields.Integer(
        string='Slots',
        compute='_compute_slot_count',
    )

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)

    @api.depends('slot_ids')
    def _compute_slot_count(self):
        for rec in self:
            rec.slot_count = len(rec.slot_ids)

    def action_view_bookings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} — Bookings',
            'res_model': 'booking_lance.booking',
            'view_mode': 'list,form,calendar',
            'domain': [('service_id', '=', self.id)],
        }


class BookingLanceServiceCategory(models.Model):
    _name = 'booking_lance.service.category'
    _description = 'Service Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Char(translate=True)
    service_ids = fields.One2many(
        'booking_lance.service',
        'category_id',
        string='Services',
    )
