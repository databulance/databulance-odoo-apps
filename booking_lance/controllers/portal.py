from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime


class BookingLancePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'booking_count' in counters:
            values['booking_count'] = request.env[
                'booking_lance.booking'
            ].search_count([
                ('partner_id', '=',
                 request.env.user.partner_id.id)
            ])
        return values

    # ------------------------------------------------------------------
    # /booking — service picker
    # ------------------------------------------------------------------
    @http.route('/booking', type='http', auth='public',
                website=True)
    def booking_home(self, **kwargs):
        website = request.website
        config = request.env['booking_lance.config'].sudo().search(
            [('website_id', '=', website.id)], limit=1
        )
        services = request.env['booking_lance.service'].sudo().search(
            [('active', '=', True)]
        )
        categories = request.env[
            'booking_lance.service.category'
        ].sudo().search([])

        return request.render(
            'booking_lance.portal_booking_home', {
                'services': services,
                'categories': categories,
                'config': config,
                'page_name': 'booking',
            }
        )

    # ------------------------------------------------------------------
    # /booking/<service_id> — slot picker
    # ------------------------------------------------------------------
    @http.route('/booking/<int:service_id>', type='http',
                auth='public', website=True)
    def booking_slots(self, service_id, **kwargs):
        service = request.env['booking_lance.service'].sudo().browse(
            service_id
        )
        if not service.exists():
            return request.redirect('/booking')

        website = request.website
        slots = request.env['booking_lance.slot'].sudo().search(
            [
                ('service_id', '=', service_id),
                ('is_available', '=', True),
                ('start_datetime', '>=', datetime.now()),
            ],
            order='start_datetime',
        )

        # Group slots by date
        slots_by_date = {}
        for slot in slots:
            date_key = slot.start_datetime.strftime('%A, %d %B %Y')
            if date_key not in slots_by_date:
                slots_by_date[date_key] = []
            slots_by_date[date_key].append(slot)

        config = request.env['booking_lance.config'].sudo().search(
            [('website_id', '=', website.id)], limit=1
        )

        return request.render(
            'booking_lance.portal_booking_slots', {
                'service': service,
                'slots': slots,
                'slots_by_date': slots_by_date,
                'config': config,
                'page_name': 'booking',
            }
        )

    # ------------------------------------------------------------------
    # /booking/confirm — review before submitting
    # ------------------------------------------------------------------
    @http.route('/booking/review', type='http',
                auth='user', website=True, methods=['POST'],
                csrf=True)
    def booking_review(self, **post):
        slot_id = int(post.get('slot_id', 0))
        service_id = int(post.get('service_id', 0))
        notes = post.get('notes', '')

        slot = request.env['booking_lance.slot'].sudo().browse(
            slot_id
        )
        service = request.env['booking_lance.service'].sudo().browse(
            service_id
        )

        if not slot.exists() or not service.exists():
            return request.redirect('/booking')

        if not slot.is_available and service.allow_waitlist:
            return request.render(
                'booking_lance.portal_booking_waitlist', {
                    'slot': slot,
                    'service': service,
                    'notes': notes,
                    'page_name': 'booking',
                }
            )

        if not slot.is_available:
            return request.redirect(
                f'/booking/{service_id}?error=unavailable'
            )

        return request.render(
            'booking_lance.portal_booking_review', {
                'slot': slot,
                'service': service,
                'notes': notes,
                'page_name': 'booking',
            }
        )

    # ------------------------------------------------------------------
    # /booking/submit — create booking
    # ------------------------------------------------------------------
    @http.route('/booking/submit', type='http',
                auth='user', website=True, methods=['POST'],
                csrf=True)
    def booking_submit(self, **post):
        slot_id = int(post.get('slot_id', 0))
        service_id = int(post.get('service_id', 0))
        notes = post.get('notes', '')
        is_recurring = post.get('is_recurring') == '1'
        recurrence_frequency = post.get('recurrence_frequency', 'weekly')
        recurrence_end = post.get('recurrence_end_date', '')

        partner = request.env.user.partner_id
        slot = request.env['booking_lance.slot'].sudo().browse(slot_id)
        service = request.env['booking_lance.service'].sudo().browse(
            service_id
        )

        if not slot.exists() or not service.exists():
            return request.redirect('/booking')

        # Handle waitlist
        if not slot.is_available:
            if service.allow_waitlist:
                position = request.env[
                    'booking_lance.waitlist'
                ].sudo()._get_next_position(slot_id)
                request.env['booking_lance.waitlist'].sudo().create({
                    'slot_id': slot_id,
                    'partner_id': partner.id,
                    'position': position,
                })
                return request.render(
                    'booking_lance.portal_booking_waitlisted', {
                        'service': service,
                        'slot': slot,
                        'page_name': 'booking',
                    }
                )
            return request.redirect(
                f'/booking/{service_id}?error=unavailable'
            )

        # Create booking
        booking = request.env['booking_lance.booking'].sudo().create({
            'partner_id': partner.id,
            'service_id': service_id,
            'slot_id': slot_id,
            'notes': notes,
            'website_id': request.website.id,
            'is_recurring': is_recurring,
        })
        booking.sudo().action_confirm()

        # Handle recurrence
        if is_recurring and service.allow_recurring \
                and recurrence_end:
            from datetime import date
            try:
                end_date = date.fromisoformat(recurrence_end)
                recurrence = request.env[
                    'booking_lance.recurrence'
                ].sudo().create({
                    'booking_id': booking.id,
                    'frequency': recurrence_frequency,
                    'end_date': end_date,
                })
                booking.sudo().write({
                    'recurrence_id': recurrence.id
                })
                recurrence.sudo(
                ).action_generate_recurring_bookings()
            except Exception:
                pass

        return request.redirect(
            f'/booking/done/{booking.id}'
        )

    # ------------------------------------------------------------------
    # /booking/done/<id> — confirmation page
    # ------------------------------------------------------------------
    @http.route('/booking/done/<int:booking_id>', type='http',
                auth='user', website=True)
    def booking_done(self, booking_id, **kwargs):
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        if not booking.exists():
            return request.redirect('/my/bookings')

        if booking.partner_id != request.env.user.partner_id:
            return request.redirect('/my/bookings')

        config = request.env['booking_lance.config'].sudo().search(
            [('website_id', '=', request.website.id)], limit=1
        )

        return request.render(
            'booking_lance.portal_booking_done', {
                'booking': booking,
                'config': config,
                'page_name': 'booking',
            }
        )

    # ------------------------------------------------------------------
    # /my/bookings — client dashboard
    # ------------------------------------------------------------------
    @http.route('/my/bookings', type='http', auth='user',
                website=True)
    def my_bookings(self, **kwargs):
        partner = request.env.user.partner_id
        bookings = request.env['booking_lance.booking'].sudo().search(
            [('partner_id', '=', partner.id)],
            order='start_datetime desc',
        )
        upcoming = bookings.filtered(
            lambda b: b.state in ['draft', 'confirmed']
            and b.start_datetime
            and b.start_datetime >= datetime.now()
        )
        past = bookings.filtered(
            lambda b: b.state in ['done', 'cancelled']
            or (b.start_datetime
                and b.start_datetime < datetime.now())
        )
        return request.render(
            'booking_lance.portal_my_bookings', {
                'bookings': bookings,
                'upcoming': upcoming,
                'past': past,
                'page_name': 'bookings',
            }
        )

    # ------------------------------------------------------------------
    # /booking/cancel/<id>
    # ------------------------------------------------------------------
    @http.route('/booking/cancel/<int:booking_id>', type='http',
                auth='user', website=True, methods=['POST'],
                csrf=True)
    def booking_cancel(self, booking_id, **post):
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        reason = post.get('reason', '')
        if booking.exists() \
                and booking.partner_id == request.env.user.partner_id:
            try:
                booking.sudo().action_cancel(reason=reason)
            except Exception as e:
                return request.redirect(
                    f'/my/bookings?error={str(e)}'
                )
        return request.redirect('/my/bookings')

    # ------------------------------------------------------------------
    # /booking/reschedule/<id> — show new slot picker
    # ------------------------------------------------------------------
    @http.route('/booking/reschedule/<int:booking_id>',
                type='http', auth='user', website=True)
    def booking_reschedule(self, booking_id, **kwargs):
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        if not booking.exists() \
                or booking.partner_id != request.env.user.partner_id:
            return request.redirect('/my/bookings')

        slots = request.env['booking_lance.slot'].sudo().search([
            ('service_id', '=', booking.service_id.id),
            ('is_available', '=', True),
            ('start_datetime', '>=', datetime.now()),
        ], order='start_datetime')

        slots_by_date = {}
        for slot in slots:
            date_key = slot.start_datetime.strftime('%A, %d %B %Y')
            if date_key not in slots_by_date:
                slots_by_date[date_key] = []
            slots_by_date[date_key].append(slot)

        return request.render(
            'booking_lance.portal_booking_reschedule', {
                'booking': booking,
                'slots': slots,
                'slots_by_date': slots_by_date,
                'page_name': 'bookings',
            }
        )

    # ------------------------------------------------------------------
    # /booking/reschedule/submit
    # ------------------------------------------------------------------
    @http.route('/booking/reschedule/submit', type='http',
                auth='user', website=True, methods=['POST'],
                csrf=True)
    def booking_reschedule_submit(self, **post):
        booking_id = int(post.get('booking_id', 0))
        new_slot_id = int(post.get('slot_id', 0))
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        if not booking.exists() \
                or booking.partner_id != request.env.user.partner_id:
            return request.redirect('/my/bookings')
        try:
            booking.sudo().action_reschedule(new_slot_id)
        except Exception as e:
            return request.redirect(
                f'/my/bookings?error={str(e)}'
            )
        return request.redirect(f'/booking/done/{booking_id}')

    # ------------------------------------------------------------------
    # /booking/ical/<token> — iCal download
    # ------------------------------------------------------------------
    @http.route('/booking/ical/<string:token>', type='http',
                auth='public', website=True)
    def booking_ical(self, token, **kwargs):
        booking = request.env['booking_lance.booking'].sudo().search(
            [('ical_token', '=', token)], limit=1
        )
        if not booking:
            return request.not_found()

        ical_content = self._generate_ical(booking)
        return request.make_response(
            ical_content,
            headers=[
                ('Content-Type', 'text/calendar; charset=utf-8'),
                ('Content-Disposition',
                 f'attachment; filename=booking_{booking.name}.ics'),
            ]
        )

    def _generate_ical(self, booking):
        fmt = '%Y%m%dT%H%M%SZ'
        start = booking.start_datetime.strftime(fmt)
        end = booking.end_datetime.strftime(fmt)
        now = datetime.utcnow().strftime(fmt)
        base_url = request.env[
            'ir.config_parameter'
        ].sudo().get_param('web.base.url')

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//BookingLance//Odoo 19//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:REQUEST',
            'BEGIN:VEVENT',
            f'UID:{booking.ical_token}@bookinglance',
            f'DTSTAMP:{now}',
            f'DTSTART:{start}',
            f'DTEND:{end}',
            f'SUMMARY:{booking.service_id.name} '
            f'— {booking.partner_id.name}',
            f'DESCRIPTION:Booking reference: {booking.name}',
            f'ORGANIZER:mailto:{booking.staff_id.email}'
            if booking.staff_id else 'ORGANIZER:mailto:noreply@example.com',
            f'ATTENDEE:mailto:{booking.partner_id.email}',
            f'URL:{base_url}/my/bookings',
            'STATUS:CONFIRMED',
            'BEGIN:VALARM',
            'TRIGGER:-PT1H',
            'ACTION:DISPLAY',
            'DESCRIPTION:Session reminder — 1 hour',
            'END:VALARM',
            'END:VEVENT',
            'END:VCALENDAR',
        ]
        return '\r\n'.join(lines)
