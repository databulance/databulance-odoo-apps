from odoo import models, fields, api


class BookingLanceStaff(models.Model):
    _name = 'booking_lance.staff'
    _description = 'Bookable Staff Member'
    _order = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='set null',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Portal / System User',
    )
    email = fields.Char(
        string='Email',
        required=True,
        tracking=True,
    )
    phone = fields.Char(string='Phone')
    image = fields.Binary(string='Photo')
    bio = fields.Text(string='Bio', translate=True)
    job_title = fields.Char(string='Job Title', translate=True)
    service_ids = fields.Many2many(
        'booking_lance.service',
        'booking_lance_service_staff_rel',
        'staff_id',
        'service_id',
        string='Services Offered',
    )
    website_ids = fields.Many2many(
        'website',
        string='Available On Websites',
    )
    schedule_ids = fields.One2many(
        'booking_lance.schedule',
        'staff_id',
        string='Weekly Schedule',
    )
    max_bookings_per_day = fields.Integer(
        string='Max Bookings Per Day',
        default=8,
    )
    slot_ids = fields.One2many(
        'booking_lance.slot',
        'staff_id',
        string='Slots',
    )
    booking_ids = fields.One2many(
        'booking_lance.booking',
        'staff_id',
        string='Bookings',
    )
    booking_count = fields.Integer(
        string='Total Bookings',
        compute='_compute_booking_count',
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')

    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(
                rec.booking_ids.filtered(
                    lambda b: b.state not in ['cancelled']
                )
            )

    def action_generate_slots(self):
        self.ensure_one()
        self.env['booking_lance.slot'].sudo()._generate_slots_for_staff(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Slots Generated',
                'message': f'Slots generated for {self.name}.',
                'type': 'success',
            },
        }

    def action_view_bookings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} — Bookings',
            'res_model': 'booking_lance.booking',
            'view_mode': 'list,form,calendar',
            'domain': [('staff_id', '=', self.id)],
        }
