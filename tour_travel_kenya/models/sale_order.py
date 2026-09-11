from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        self.order_line._init_bookings()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('partner_id'):
            for order in self:
                order.order_line.booking_ids.sudo().write({'partner_id': vals['partner_id']})
        return res

    def _cart_find_product_line(self, *args, tour_package_date_id=False, tour_pricing_id=False, **kwargs):
        lines = super()._cart_find_product_line(*args, **kwargs)
        if not tour_package_date_id and not tour_pricing_id:
            return lines
        return lines.filtered(
            lambda line: line.tour_package_date_id.id == tour_package_date_id
            and line.tour_pricing_id.id == tour_pricing_id)

    def _prepare_order_line_values(self, product_id, *args, tour_package_date_id=False, tour_pricing_id=False, **kwargs):
        values = super()._prepare_order_line_values(product_id, *args, **kwargs)
        if not tour_pricing_id:
            return values

        pricing = self.env['tour.package.pricing'].browse(tour_pricing_id)
        if pricing.product_id.id != product_id:
            raise UserError(_("The selected pricing tier doesn't match this product."))

        values['tour_package_id'] = pricing.package_id.id
        values['tour_pricing_id'] = pricing.id
        values['tour_package_date_id'] = tour_package_date_id
        return values

    def _verify_updated_quantity(self, order_line, product_id, new_qty, uom_id, *, tour_package_date_id=False, tour_pricing_id=False, **kwargs):
        new_qty, warning = super()._verify_updated_quantity(
            order_line, product_id, new_qty, uom_id, **kwargs)

        package_date = order_line.tour_package_date_id or self.env['tour.package.date'].browse(tour_package_date_id)
        if not package_date:
            return new_qty, warning

        # tour.booking records are only created on order confirmation (see
        # sale_order_line._init_bookings), so a cart line never has its own
        # existing reservation counted in seats_available yet - no need to add it back.
        available = package_date.seats_available if package_date.seats_limited and package_date.seats_max else None
        if available is not None:
            if available <= 0:
                return 0, _(
                    'Sorry, the %(date)s departure for %(package)s is sold out.',
                    date=package_date.date_start, package=package_date.package_id.name)
            if new_qty > available:
                return available, _(
                    'Sorry, only %(count)s seat(s) left for the %(date)s departure of %(package)s.',
                    count=available, date=package_date.date_start, package=package_date.package_id.name)
        return new_qty, warning
