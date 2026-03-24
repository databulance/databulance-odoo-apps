from odoo import http
from odoo.http import request
from datetime import datetime
import json


class BookingLanceAPI(http.Controller):

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*'),
            ],
            status=status,
        )

    def _error(self, message, status=400):
        return self._json_response(
            {'success': False, 'error': message}, status
        )

    # ------------------------------------------------------------------
    # GET /api/booking/services
    # ------------------------------------------------------------------
    @http.route('/api/booking/services', type='http',
                auth='public', methods=['GET'], csrf=False)
    def api_services(self, **kwargs):
        services = request.env['booking_lance.service'].sudo().search(
            [('active', '=', True)]
        )
        data = [{
            'id': s.id,
            'name': s.name,
            'duration': s.duration,
            'buffer_time': s.buffer_time,
            'max_capacity': s.max_capacity,
            'payment_mode': s.payment_mode,
            'allow_recurring': s.allow_recurring,
            'allow_waitlist': s.allow_waitlist,
            'category': s.category_id.name if s.category_id else None,
        } for s in services]
        return self._json_response({'success': True, 'services': data})

    # ------------------------------------------------------------------
    # GET /api/booking/slots?service_id=X
    # ------------------------------------------------------------------
    @http.route('/api/booking/slots', type='http',
                auth='public', methods=['GET'], csrf=False)
    def api_slots(self, service_id=None, **kwargs):
        if not service_id:
            return self._error('service_id is required')
        domain = [
            ('is_available', '=', True),
            ('start_datetime', '>=', datetime.now()),
        ]
        try:
            domain.append(('service_id', '=', int(service_id)))
        except ValueError:
            return self._error('Invalid service_id')

        slots = request.env['booking_lance.slot'].sudo().search(
            domain, order='start_datetime', limit=100
        )
        data = [{
            'id': s.id,
            'start': str(s.start_datetime),
            'end': str(s.end_datetime),
            'staff': s.staff_id.name if s.staff_id else None,
            'available': s.is_available,
            'booked_count': s.booked_count,
            'capacity': s.service_id.max_capacity,
        } for s in slots]
        return self._json_response({'success': True, 'slots': data})

    # ------------------------------------------------------------------
    # POST /api/booking/create
    # ------------------------------------------------------------------
    @http.route('/api/booking/create', type='http',
                auth='user', methods=['POST'], csrf=False)
    def api_create(self, **post):
        try:
            slot_id = int(post.get('slot_id', 0))
            service_id = int(post.get('service_id', 0))
        except (ValueError, TypeError):
            return self._error('Invalid slot_id or service_id')

        if not slot_id or not service_id:
            return self._error('slot_id and service_id are required')

        partner = request.env.user.partner_id
        slot = request.env['booking_lance.slot'].sudo().browse(slot_id)
        service = request.env['booking_lance.service'].sudo().browse(
            service_id
        )

        if not slot.exists():
            return self._error('Slot not found', 404)
        if not service.exists():
            return self._error('Service not found', 404)
        if not slot.is_available:
            return self._error('Slot is not available', 409)

        booking = request.env['booking_lance.booking'].sudo().create({
            'partner_id': partner.id,
            'service_id': service_id,
            'slot_id': slot_id,
            'notes': post.get('notes', ''),
        })
        booking.sudo().action_confirm()

        return self._json_response({
            'success': True,
            'booking': {
                'id': booking.id,
                'reference': booking.name,
                'state': booking.state,
                'start': str(booking.start_datetime),
                'end': str(booking.end_datetime),
                'ical_url': booking._get_ical_url(),
            }
        }, status=201)

    # ------------------------------------------------------------------
    # GET /api/booking/<id>
    # ------------------------------------------------------------------
    @http.route('/api/booking/<int:booking_id>', type='http',
                auth='user', methods=['GET'], csrf=False)
    def api_get(self, booking_id, **kwargs):
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        if not booking.exists():
            return self._error('Booking not found', 404)
        if booking.partner_id != request.env.user.partner_id:
            return self._error('Forbidden', 403)

        return self._json_response({
            'success': True,
            'booking': {
                'id': booking.id,
                'reference': booking.name,
                'service': booking.service_id.name,
                'staff': booking.staff_id.name
                if booking.staff_id else None,
                'start': str(booking.start_datetime),
                'end': str(booking.end_datetime),
                'state': booking.state,
                'payment_mode': booking.payment_mode,
                'is_recurring': booking.is_recurring,
                'notes': booking.notes,
                'ical_url': booking._get_ical_url(),
            }
        })

    # ------------------------------------------------------------------
    # POST /api/booking/<id>/cancel
    # ------------------------------------------------------------------
    @http.route('/api/booking/<int:booking_id>/cancel',
                type='http', auth='user', methods=['POST'],
                csrf=False)
    def api_cancel(self, booking_id, **post):
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        if not booking.exists():
            return self._error('Booking not found', 404)
        if booking.partner_id != request.env.user.partner_id:
            return self._error('Forbidden', 403)
        try:
            booking.sudo().action_cancel(
                reason=post.get('reason', '')
            )
        except Exception as e:
            return self._error(str(e))

        return self._json_response({
            'success': True,
            'message': f'Booking {booking.name} cancelled.',
        })

    # ------------------------------------------------------------------
    # POST /api/booking/<id>/reschedule
    # ------------------------------------------------------------------
    @http.route('/api/booking/<int:booking_id>/reschedule',
                type='http', auth='user', methods=['POST'],
                csrf=False)
    def api_reschedule(self, booking_id, **post):
        booking = request.env['booking_lance.booking'].sudo().browse(
            booking_id
        )
        if not booking.exists():
            return self._error('Booking not found', 404)
        if booking.partner_id != request.env.user.partner_id:
            return self._error('Forbidden', 403)
        try:
            new_slot_id = int(post.get('new_slot_id', 0))
            booking.sudo().action_reschedule(new_slot_id)
        except Exception as e:
            return self._error(str(e))

        return self._json_response({
            'success': True,
            'message': f'Booking {booking.name} rescheduled.',
            'new_start': str(booking.start_datetime),
        })
