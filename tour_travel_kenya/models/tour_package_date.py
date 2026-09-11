from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TourPackageDate(models.Model):
    _name = 'tour.package.date'
    _description = 'Tour Departure Date'
    _order = 'date_start, id'

    package_id = fields.Many2one('tour.package', string='Package', required=True, ondelete='cascade', index=True)
    date_start = fields.Date(string='Departure Date', required=True)
    date_end = fields.Date(string='Return Date', compute='_compute_date_end', store=True)
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('done', 'Departed'),
    ], default='open', required=True)

    seats_max = fields.Integer(
        string='Max Travelers', compute='_compute_seats_max', store=True, readonly=False, precompute=True,
        help="Maximum number of travelers for this departure. Defaults to the package's setting.")
    seats_limited = fields.Boolean(related='package_id.seats_limited')
    booking_ids = fields.One2many('tour.booking', 'package_date_id', string='Bookings')
    seats_reserved = fields.Integer(string='Travelers Reserved', compute='_compute_seats')
    seats_used = fields.Integer(string='Travelers Confirmed', compute='_compute_seats')
    seats_available = fields.Integer(string='Available Seats', compute='_compute_seats')
    is_sold_out = fields.Boolean(compute='_compute_is_sold_out')

    @api.depends('package_id.seats_max')
    def _compute_seats_max(self):
        for date in self:
            if not date.seats_max:
                date.seats_max = date.package_id.seats_max

    @api.depends('package_id.duration_days', 'date_start')
    def _compute_date_end(self):
        for date in self:
            if date.date_start and date.package_id.duration_days:
                date.date_end = date.date_start + timedelta(days=date.package_id.duration_days - 1)
            else:
                date.date_end = date.date_start

    @api.depends('seats_max', 'booking_ids.traveler_count', 'booking_ids.state', 'booking_ids.active')
    def _compute_seats(self):
        for date in self:
            date.seats_reserved = date.seats_used = date.seats_available = 0

        state_field = {
            'open': 'seats_reserved',
            'done': 'seats_used',
        }
        base_vals = dict.fromkeys(state_field.values(), 0)
        results = {date_id: dict(base_vals) for date_id in self.ids}
        if self.ids:
            query = """ SELECT package_date_id, state, sum(traveler_count)
                        FROM tour_booking
                        WHERE package_date_id IN %s AND state IN ('open', 'done') AND active = true
                        GROUP BY package_date_id, state
                    """
            self.env['tour.booking'].flush_model(['package_date_id', 'state', 'traveler_count', 'active'])
            self.env.cr.execute(query, (tuple(self.ids),))
            for date_id, state, total in self.env.cr.fetchall():
                results[date_id][state_field[state]] = total or 0

        for date in self:
            date.update(results.get(date._origin.id or date.id, base_vals))
            if date.seats_max > 0:
                date.seats_available = date.seats_max - (date.seats_reserved + date.seats_used)

    @api.depends('seats_limited', 'seats_available', 'seats_max', 'state')
    def _compute_is_sold_out(self):
        for date in self:
            date.is_sold_out = date.state != 'closed' and date.seats_limited and date.seats_max and not date.seats_available > 0

    def _verify_seats_availability(self, extra_travelers=0):
        """Raise if this departure date cannot accommodate `extra_travelers` more travelers."""
        self.ensure_one()
        if self.state != 'open':
            raise ValidationError(_('This departure date is not open for booking.'))
        if self.seats_limited and self.seats_max and self.seats_available - extra_travelers < 0:
            raise ValidationError(_(
                'Not enough seats available for %(package)s on %(date)s: only %(available)s seat(s) left.',
                package=self.package_id.name, date=self.date_start, available=max(self.seats_available, 0),
            ))

    def _compute_display_name(self):
        for date in self:
            date.display_name = '%s - %s' % (date.package_id.name, date.date_start) if date.date_start else date.package_id.name

    @api.ondelete(at_uninstall=False)
    def _unlink_except_if_bookings(self):
        if self.booking_ids:
            raise UserError(_(
                "The following departure dates cannot be deleted while they have bookings linked to them:\n- %s",
                '\n- '.join(self.mapped('display_name'))))
