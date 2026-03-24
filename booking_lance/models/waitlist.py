from odoo import models, fields, api


class BookingLanceWaitlist(models.Model):
    _name = 'booking_lance.waitlist'
    _description = 'Booking Waitlist Entry'
    _order = 'slot_id, position'

    slot_id = fields.Many2one(
        'booking_lance.slot',
        string='Slot',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
    )
    service_id = fields.Many2one(
        related='slot_id.service_id',
        string='Service',
        store=True,
    )
    position = fields.Integer(
        string='Queue Position',
        required=True,
    )
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('notified', 'Notified'),
        ('booked', 'Booked'),
        ('expired', 'Expired'),
    ], string='State', default='waiting')
    notified_at = fields.Datetime(string='Notified At')
    notes = fields.Char(string='Notes')

    @api.model
    def _get_next_position(self, slot_id):
        last = self.search(
            [('slot_id', '=', slot_id)],
            order='position desc',
            limit=1,
        )
        return (last.position + 1) if last else 1

    def action_notify_client(self):
        self.ensure_one()
        template = self.env.ref(
            'booking_lance.email_template_waitlist_notify',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)
        self.write({
            'state': 'notified',
            'notified_at': fields.Datetime.now(),
        })
