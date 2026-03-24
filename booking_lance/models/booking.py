from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class BookingLanceBooking(models.Model):
    _name = 'booking_lance.booking'
    _description = 'Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True,
    )
    service_id = fields.Many2one(
        'booking_lance.service',
        string='Service',
        required=True,
        tracking=True,
    )
    staff_id = fields.Many2one(
        'booking_lance.staff',
        string='Staff Member',
        tracking=True,
    )
    slot_id = fields.Many2one(
        'booking_lance.slot',
        string='Time Slot',
        required=True,
        tracking=True,
    )
    start_datetime = fields.Datetime(
        related='slot_id.start_datetime',
        string='Start',
        store=True,
    )
    end_datetime = fields.Datetime(
        related='slot_id.end_datetime',
        string='End',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ], string='Status', default='draft',
       required=True, tracking=True)
    payment_mode = fields.Selection(
        related='service_id.payment_mode',
        string='Payment Mode',
        store=True,
    )
    notes = fields.Text(string='Client Notes')
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
    )
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
    )
    ical_token = fields.Char(
        string='iCal Token',
        copy=False,
        readonly=True,
    )
    recurrence_id = fields.Many2one(
        'booking_lance.recurrence',
        string='Recurrence',
    )
    is_recurring = fields.Boolean(
        string='Is Recurring',
        default=False,
    )
    waitlist_id = fields.Many2one(
        'booking_lance.waitlist',
        string='Waitlist Entry',
    )
    website_id = fields.Many2one(
        'website',
        string='Website',
    )

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'booking_lance.booking'
                    ) or 'New'
                )
            if not vals.get('ical_token'):
                import uuid
                vals['ical_token'] = str(uuid.uuid4())
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if not rec.slot_id.is_available:
                raise UserError(
                    'This time slot is no longer available.'
                )
            # Auto-assign staff from slot
            if not rec.staff_id:
                rec.staff_id = rec.slot_id.staff_id
            rec.slot_id.state = 'booked'
            rec.state = 'confirmed'
            rec._create_calendar_event()
            rec._send_mail('confirmation')
            rec._fire_webhook('confirmed')

    def action_done(self):
        self.write({'state': 'done'})
        for rec in self:
            rec._fire_webhook('done')

    def action_cancel(self, reason=None):
        for rec in self:
            rec._check_cancellation_policy()
            if rec.calendar_event_id:
                rec.calendar_event_id.sudo().unlink()
            rec.slot_id.state = 'available'
            rec.state = 'cancelled'
            if reason:
                rec.cancellation_reason = reason
            rec._send_mail('cancellation')
            rec._fire_webhook('cancelled')
            rec._notify_waitlist()

    def action_reschedule(self, new_slot_id):
        for rec in self:
            rec._check_reschedule_policy()
            old_slot = rec.slot_id
            new_slot = self.env['booking_lance.slot'].browse(
                new_slot_id
            )
            if not new_slot.is_available:
                raise UserError(
                    'The selected slot is not available.'
                )
            old_slot.state = 'available'
            rec.slot_id = new_slot
            rec.staff_id = new_slot.staff_id
            new_slot.state = 'booked'
            rec.state = 'confirmed'
            if rec.calendar_event_id:
                rec.calendar_event_id.write({
                    'start': new_slot.start_datetime,
                    'stop': new_slot.end_datetime,
                })
            rec._send_mail('reschedule')
            rec._fire_webhook('rescheduled')

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Policy checks
    # ------------------------------------------------------------------
    def _check_cancellation_policy(self):
        for rec in self:
            hours_limit = (
                rec.service_id.cancellation_hours
                or rec.env['booking_lance.config'].search(
                    [], limit=1
                ).cancellation_hours_limit
                or 24
            )
            if hours_limit and rec.start_datetime:
                deadline = (
                    rec.start_datetime
                    - timedelta(hours=hours_limit)
                )
                if datetime.now() > deadline:
                    raise UserError(
                        f'Cancellations must be made at least '
                        f'{hours_limit} hours before the session.'
                    )

    def _check_reschedule_policy(self):
        for rec in self:
            hours_limit = (
                rec.service_id.reschedule_hours
                or rec.env['booking_lance.config'].search(
                    [], limit=1
                ).reschedule_hours_limit
                or 24
            )
            if hours_limit and rec.start_datetime:
                deadline = (
                    rec.start_datetime
                    - timedelta(hours=hours_limit)
                )
                if datetime.now() > deadline:
                    raise UserError(
                        f'Rescheduling must be done at least '
                        f'{hours_limit} hours before the session.'
                    )

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------
    def _create_calendar_event(self):
        for rec in self:
            if rec.calendar_event_id:
                continue
            attendees = [rec.partner_id.id]
            if rec.staff_id.user_id:
                attendees.append(
                    rec.staff_id.user_id.partner_id.id
                )
            event = self.env['calendar.event'].sudo().create({
                'name': (
                    f'{rec.service_id.name} '
                    f'— {rec.partner_id.name}'
                ),
                'start': rec.start_datetime,
                'stop': rec.end_datetime,
                'partner_ids': [(6, 0, attendees)],
                'description': rec.notes or '',
                'location': '',
            })
            rec.calendar_event_id = event.id

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------
    def _send_mail(self, mail_type):
        subject_map = {
            'confirmation': 'Booking Confirmed',
            'cancellation': 'Booking Cancelled',
            'reschedule':   'Booking Rescheduled',
            'reminder':     'Session Reminder — 24 hours',
        }
        builder_map = {
            'confirmation': '_build_confirmation_body',
            'cancellation': '_build_cancellation_body',
            'reschedule':   '_build_reschedule_body',
            'reminder':     '_build_reminder_body',
        }
        subject = subject_map.get(mail_type)
        builder = builder_map.get(mail_type)
        if not subject or not builder:
            return
        for rec in self:
            try:
                body = getattr(rec, builder)(rec)
                subject_full = f"{subject} — {rec.name}"
                msg = self.env['mail.message'].sudo().create({
                    'body': body,
                    'subject': subject_full,
                    'message_type': 'email',
                    'email_from': 'info@databulance.com',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                })
                mail = self.env['mail.mail'].sudo().create({
                    'mail_message_id': msg.id,
                    'email_to': rec.partner_id.email,
                    'body_html': body,
                    'state': 'outgoing',
                })
                mail.send()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"BookingLance mail error: {e}"
                )

    # ------------------------------------------------------------------
    # iCal
    # ------------------------------------------------------------------
    def _get_ical_url(self):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        return f'{base}/booking/ical/{self.ical_token}'

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------
    def _fire_webhook(self, event):
        import json
        import requests
        webhooks = self.env['booking_lance.webhook'].search([
            ('event', 'in', [event, 'all']),
            ('active', '=', True),
        ])
        for rec in self:
            payload = {
                'event': event,
                'booking_ref': rec.name,
                'client': rec.partner_id.name,
                'client_email': rec.partner_id.email,
                'service': rec.service_id.name,
                'staff': rec.staff_id.name if rec.staff_id else '',
                'start': str(rec.start_datetime),
                'end': str(rec.end_datetime),
                'state': rec.state,
            }
            for wh in webhooks:
                try:
                    headers = {'Content-Type': 'application/json'}
                    if wh.secret_key:
                        headers['X-BookingLance-Secret'] = (
                            wh.secret_key
                        )
                    requests.post(
                        wh.url,
                        data=json.dumps(payload),
                        headers=headers,
                        timeout=5,
                    )
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Waitlist
    # ------------------------------------------------------------------
    def _notify_waitlist(self):
        for rec in self:
            next_entry = self.env[
                'booking_lance.waitlist'
            ].search([
                ('slot_id', '=', rec.slot_id.id),
                ('state', '=', 'waiting'),
            ], order='position', limit=1)
            if next_entry:
                next_entry.action_notify_client()

    # ------------------------------------------------------------------
    # Cron — reminders
    # ------------------------------------------------------------------
    @api.model
    def _cron_send_reminders(self):
        """Send reminder 24h before session."""
        now = fields.Datetime.now()
        remind_from = now + timedelta(hours=23)
        remind_to = now + timedelta(hours=25)
        bookings = self.search([
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', remind_from),
            ('start_datetime', '<=', remind_to),
        ])
        for booking in bookings:
            booking._send_mail('reminder')

    def _build_confirmation_body(self, rec):
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        )
        sel = self._fields['payment_mode'].selection
        payment_labels = dict(sel(self) if callable(sel) else sel)
        return (
            '<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
            '<div style="background:#0d1120;padding:32px 24px;text-align:center;border-radius:8px 8px 0 0;">'
            '<h1 style="color:#ffffff;font-size:22px;margin:0 0 8px;">Booking Confirmed</h1>'
            '<p style="color:#9c27b0;font-family:monospace;font-size:12px;margin:0;">' + rec.name + '</p>'
            '</div>'
            '<div style="background:#f9fafb;padding:32px 24px;border-radius:0 0 8px 8px;">'
            '<p style="color:#374151;">Dear ' + rec.partner_id.name + ',</p>'
            '<p style="color:#374151;">Your booking has been confirmed.</p>'
            '<table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:24px;">'
            '<tr><td style="padding:10px;background:#fff;border:1px solid #e5e7eb;font-weight:600;">Service</td>'
            '<td style="padding:10px;background:#fff;border:1px solid #e5e7eb;">' + rec.service_id.name + '</td></tr>'
            '<tr><td style="padding:10px;background:#f3f4f6;border:1px solid #e5e7eb;font-weight:600;">Staff</td>'
            '<td style="padding:10px;background:#f3f4f6;border:1px solid #e5e7eb;">' + (rec.staff_id.name if rec.staff_id else 'To be assigned') + '</td></tr>'
            '<tr><td style="padding:10px;background:#fff;border:1px solid #e5e7eb;font-weight:600;">Date &amp; Time</td>'
            '<td style="padding:10px;background:#fff;border:1px solid #e5e7eb;">' + str(rec.start_datetime) + '</td></tr>'
            '<tr><td style="padding:10px;background:#f3f4f6;border:1px solid #e5e7eb;font-weight:600;">Duration</td>'
            '<td style="padding:10px;background:#f3f4f6;border:1px solid #e5e7eb;">' + str(rec.service_id.duration) + ' hour(s)</td></tr>'
            '<tr><td style="padding:10px;background:#fff;border:1px solid #e5e7eb;font-weight:600;">Reference</td>'
            '<td style="padding:10px;background:#fff;border:1px solid #e5e7eb;">' + rec.name + '</td></tr>'
            '<tr><td style="padding:10px;background:#f3f4f6;border:1px solid #e5e7eb;font-weight:600;">Payment</td>'
            '<td style="padding:10px;background:#f3f4f6;border:1px solid #e5e7eb;">' + payment_labels.get(rec.payment_mode, '') + '</td></tr>'
            '</table>'
            '<p style="color:#6b7280;font-size:13px;">Manage bookings: '
            '<a href="' + base_url + '/my/bookings" style="color:#9c27b0;">client portal</a></p>'
            '</div>'
            '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:11px;">'
            'Powered by BookingLance · <a href="https://databulance.com" style="color:#9c27b0;">databulance.com</a>'
            '</div></div>'
        )

    def _build_cancellation_body(self, rec):
        return (
            '<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
            '<div style="background:#7f1d1d;padding:32px 24px;text-align:center;border-radius:8px 8px 0 0;">'
            '<h1 style="color:#ffffff;font-size:22px;margin:0 0 8px;">Booking Cancelled</h1>'
            '<p style="color:#fca5a5;font-family:monospace;font-size:12px;margin:0;">' + rec.name + '</p>'
            '</div>'
            '<div style="background:#f9fafb;padding:32px 24px;border-radius:0 0 8px 8px;">'
            '<p style="color:#374151;">Dear ' + rec.partner_id.name + ',</p>'
            '<p style="color:#374151;">Your booking for <strong>' + rec.service_id.name + '</strong> '
            'on <strong>' + str(rec.start_datetime) + '</strong> has been cancelled.</p>'
            '<p><a href="https://databulance.com/booking" style="color:#9c27b0;">Book a new session</a></p>'
            '</div>'
            '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:11px;">'
            'Powered by BookingLance · databulance.com</div></div>'
        )

    def _build_reschedule_body(self, rec):
        return (
            '<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
            '<div style="background:#1e3a5f;padding:32px 24px;text-align:center;border-radius:8px 8px 0 0;">'
            '<h1 style="color:#ffffff;font-size:22px;margin:0 0 8px;">Booking Rescheduled</h1>'
            '<p style="color:#93c5fd;font-family:monospace;font-size:12px;margin:0;">' + rec.name + '</p>'
            '</div>'
            '<div style="background:#f9fafb;padding:32px 24px;border-radius:0 0 8px 8px;">'
            '<p style="color:#374151;">Dear ' + rec.partner_id.name + ',</p>'
            '<p style="color:#374151;">Your booking has been rescheduled to <strong>' + str(rec.start_datetime) + '</strong>.</p>'
            '<p>Service: <strong>' + rec.service_id.name + '</strong></p>'
            '</div>'
            '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:11px;">'
            'Powered by BookingLance · databulance.com</div></div>'
        )

    def _build_reminder_body(self, rec):
        return (
            '<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
            '<div style="background:#0d1120;padding:32px 24px;text-align:center;border-radius:8px 8px 0 0;">'
            '<h1 style="color:#ffffff;font-size:22px;margin:0 0 8px;">Session Reminder</h1>'
            '<p style="color:#9c27b0;font-family:monospace;font-size:12px;margin:0;">' + rec.name + '</p>'
            '</div>'
            '<div style="background:#f9fafb;padding:32px 24px;border-radius:0 0 8px 8px;">'
            '<p style="color:#374151;">Dear ' + rec.partner_id.name + ',</p>'
            '<p style="color:#374151;">Your session is in approximately 24 hours.</p>'
            '<p>Service: <strong>' + rec.service_id.name + '</strong><br/>'
            'Date: <strong>' + str(rec.start_datetime) + '</strong><br/>'
            'Staff: <strong>' + (rec.staff_id.name if rec.staff_id else 'To be assigned') + '</strong></p>'
            '</div>'
            '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:11px;">'
            'Powered by BookingLance · databulance.com</div></div>'
        )
