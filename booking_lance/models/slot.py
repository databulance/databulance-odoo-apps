from odoo import models, fields, api
from datetime import datetime, timedelta
import math


class BookingLanceSlot(models.Model):
    _name = 'booking_lance.slot'
    _description = 'Booking Slot'
    _order = 'start_datetime'

    name = fields.Char(
        string='Slot',
        compute='_compute_name',
        store=True,
    )
    service_id = fields.Many2one(
        'booking_lance.service',
        string='Service',
        required=True,
        ondelete='cascade',
    )
    staff_id = fields.Many2one(
        'booking_lance.staff',
        string='Staff Member',
        required=True,
        ondelete='cascade',
    )
    website_id = fields.Many2one(
        'website',
        string='Website',
    )
    start_datetime = fields.Datetime(
        string='Start',
        required=True,
    )
    end_datetime = fields.Datetime(
        string='End',
        required=True,
    )
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('blocked', 'Blocked'),
        ('waitlist', 'Waitlist Only'),
    ], string='State', default='available', required=True)
    booking_ids = fields.One2many(
        'booking_lance.booking',
        'slot_id',
        string='Bookings',
    )
    booked_count = fields.Integer(
        string='Booked',
        compute='_compute_booked_count',
        store=True,
    )
    is_available = fields.Boolean(
        string='Available',
        compute='_compute_is_available',
        store=True,
    )
    is_manual = fields.Boolean(
        string='Manually Created',
        default=False,
        help='Manually created slots are not overwritten by cron.',
    )
    notes = fields.Char(string='Notes')

    @api.depends('start_datetime', 'staff_id', 'service_id')
    def _compute_name(self):
        for rec in self:
            if rec.start_datetime and rec.staff_id and rec.service_id:
                rec.name = (
                    f"{rec.service_id.name} — "
                    f"{rec.staff_id.name} — "
                    f"{rec.start_datetime.strftime('%a %d %b %H:%M')}"
                )
            else:
                rec.name = 'New Slot'

    @api.depends('booking_ids', 'booking_ids.state')
    def _compute_booked_count(self):
        for rec in self:
            rec.booked_count = len(
                rec.booking_ids.filtered(
                    lambda b: b.state in ['confirmed', 'done']
                )
            )

    @api.depends('booked_count', 'service_id.max_capacity', 'state')
    def _compute_is_available(self):
        for rec in self:
            rec.is_available = (
                rec.state == 'available'
                and rec.booked_count < rec.service_id.max_capacity
            )

    def action_block(self):
        self.write({'state': 'blocked'})

    def action_unblock(self):
        self.write({'state': 'available'})

    # ----------------------------------------------------------------
    # Slot generation engine
    # ----------------------------------------------------------------
    @api.model
    def _generate_slots_for_staff(self, staff):
        """Generate slots for a staff member based on their weekly
        schedule and all their assigned services.
        Called by cron and by the manual button on staff form."""

        config = self.env['booking_lance.config'].search([], limit=1)
        days_ahead = config.slot_generation_days if config else 30

        today = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = today + timedelta(days=days_ahead)

        for service in staff.service_ids:
            slot_duration_hours = service.duration + service.buffer_time
            slot_duration_minutes = int(slot_duration_hours * 60)

            for schedule in staff.schedule_ids.filtered('active'):
                day_idx = int(schedule.day_of_week)

                # Walk through every matching weekday in the window
                current = today
                while current <= end_date:
                    if current.weekday() == day_idx:
                        # Generate slots for this day
                        day_start = current.replace(
                            hour=int(schedule.time_from),
                            minute=int(
                                (schedule.time_from % 1) * 60
                            ),
                            second=0,
                        )
                        day_end = current.replace(
                            hour=int(schedule.time_to),
                            minute=int(
                                (schedule.time_to % 1) * 60
                            ),
                            second=0,
                        )
                        slot_start = day_start
                        daily_count = 0

                        while (
                            slot_start + timedelta(
                                minutes=slot_duration_minutes
                            ) <= day_end
                            and daily_count < staff.max_bookings_per_day
                        ):
                            slot_end = slot_start + timedelta(
                                minutes=int(service.duration * 60)
                            )

                            # Skip if slot already exists (not manual)
                            existing = self.search([
                                ('staff_id', '=', staff.id),
                                ('service_id', '=', service.id),
                                ('start_datetime', '=', slot_start),
                                ('is_manual', '=', False),
                            ], limit=1)

                            if not existing:
                                self.create({
                                    'service_id': service.id,
                                    'staff_id': staff.id,
                                    'start_datetime': slot_start,
                                    'end_datetime': slot_end,
                                    'state': 'available',
                                    'is_manual': False,
                                })

                            slot_start += timedelta(
                                minutes=slot_duration_minutes
                            )
                            daily_count += 1

                    current += timedelta(days=1)

    @api.model
    def _cron_generate_all_slots(self):
        """Called by daily cron — generates slots for all active staff."""
        all_staff = self.env['booking_lance.staff'].search([
            ('active', '=', True)
        ])
        for staff in all_staff:
            self._generate_slots_for_staff(staff)

        # Clean up past available slots older than today
        self.search([
            ('start_datetime', '<', fields.Datetime.now()),
            ('state', '=', 'available'),
            ('is_manual', '=', False),
        ]).unlink()
