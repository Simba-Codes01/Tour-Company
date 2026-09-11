from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tour_package_id = fields.Many2one(
        'tour.package', string='Tour Package',
        compute='_compute_tour_package_id', store=True, readonly=False, precompute=True, index='btree_not_null')
    tour_package_date_id = fields.Many2one(
        'tour.package.date', string='Departure Date',
        compute='_compute_tour_related', store=True, readonly=False, precompute=True)
    tour_pricing_id = fields.Many2one(
        'tour.package.pricing', string='Pricing Tier',
        compute='_compute_tour_related', store=True, readonly=False, precompute=True)
    booking_ids = fields.One2many('tour.booking', 'sale_order_line_id', string='Bookings')

    @api.depends('product_id')
    def _compute_tour_package_id(self):
        pricings = self.env['tour.package.pricing'].search([('product_id', 'in', self.product_id.ids)])
        package_by_product = {pricing.product_id: pricing.package_id for pricing in pricings}
        tour_lines = self.filtered(lambda line: line.product_id in package_by_product)
        (self - tour_lines).tour_package_id = False
        for line in tour_lines:
            if line.product_id not in line.tour_package_id.pricing_ids.product_id:
                line.tour_package_id = package_by_product[line.product_id]

    @api.depends('tour_package_id', 'product_id')
    def _compute_tour_related(self):
        tour_lines = self.filtered('tour_package_id')
        (self - tour_lines).tour_package_date_id = False
        (self - tour_lines).tour_pricing_id = False
        for line in tour_lines:
            if line.tour_pricing_id.package_id != line.tour_package_id or line.tour_pricing_id.product_id != line.product_id:
                pricing = self.env['tour.package.pricing'].search([
                    ('package_id', '=', line.tour_package_id.id),
                    ('product_id', '=', line.product_id.id),
                ], limit=1)
                line.tour_pricing_id = pricing
            if line.tour_package_date_id.package_id != line.tour_package_id:
                line.tour_package_date_id = False

    @api.constrains('tour_package_id', 'tour_package_date_id', 'tour_pricing_id')
    def _check_tour_booking_fields(self):
        for line in self.filtered('tour_package_id'):
            if not line.tour_package_date_id or not line.tour_pricing_id:
                raise ValidationError(self.env._(
                    "The order line for %(product)s needs a departure date and a pricing tier selected.",
                    product=line.product_id.display_name))

    def _init_bookings(self):
        """Create/update one tour.booking per confirmed tour order line, sized by
        the line's quantity (party size), instead of one booking per unit like
        event registrations."""
        for line in self:
            if not line.tour_package_id:
                continue
            if line.booking_ids:
                line.booking_ids.write({'traveler_count': int(line.product_uom_qty)})
                continue
            values = {
                'package_id': line.tour_package_id.id,
                'package_date_id': line.tour_package_date_id.id,
                'pricing_id': line.tour_pricing_id.id,
                'traveler_count': int(line.product_uom_qty) or 1,
                'sale_order_id': line.order_id.id,
                'sale_order_line_id': line.id,
                'partner_id': line.order_id.partner_id.id,
            }
            # state/sale_status are left unset here so tour.booking's own
            # precompute (_compute_booking_status) derives them from the
            # sale order's state/amount_total - unlike event registrations,
            # a tour booking has no separate post-payment attendee-detail
            # step, so there's no reason to force it to 'draft' first.
            self.env['tour.booking'].sudo().create(values)
        return True

    def _get_display_price(self):
        if self.tour_pricing_id:
            return self._convert_to_sol_currency(
                self.tour_pricing_id.price, self.tour_pricing_id.currency_id)
        return super()._get_display_price()
