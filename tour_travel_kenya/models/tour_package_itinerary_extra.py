from odoo import fields, models


class TourPackageItineraryExtra(models.Model):
    _name = 'tour.package.itinerary.extra'
    _description = 'Itinerary Day Optional Extra'
    _order = 'sequence, id'

    day_id = fields.Many2one(
        'tour.package.itinerary.day', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, help="e.g. 'Hot Air Balloon Safari'.")
    price_adult = fields.Float(string='Adult Price', help="Per-person price, paid locally, e.g. 450.")
    price_child = fields.Float(string='Child Price', help="Per-child price, paid locally, if different.")
    currency_id = fields.Many2one(related='day_id.package_id.currency_id')

    def get_price_display(self, amount):
        self.ensure_one()
        currency = self.currency_id
        amount_str = '%.0f' % amount
        if currency.position == 'before':
            return '%s%s' % (currency.symbol, amount_str)
        return '%s %s' % (amount_str, currency.symbol)
