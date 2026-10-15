from odoo import fields, models


class TourPackageSeasonRate(models.Model):
    _name = 'tour.package.season.rate'
    _description = 'Tour Package Seasonal Group Pricing'
    _order = 'date_start'

    package_id = fields.Many2one('tour.package', required=True, ondelete='cascade', index=True)
    season_label = fields.Char(required=True, help="e.g. 'Peak Season', 'Green Season'.")
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    price_2pax = fields.Float(string='2 People (per person)')
    price_3pax = fields.Float(string='3 People (per person)')
    price_4pax = fields.Float(string='4 People (per person)')
    price_5pax = fields.Float(string='5 People (per person)')
    price_6pax = fields.Float(string='6 People (per person)')
    price_2pax_child = fields.Float(string='2 People (per child)')
    price_3pax_child = fields.Float(string='3 People (per child)')
    price_4pax_child = fields.Float(string='4 People (per child)')
    price_5pax_child = fields.Float(string='5 People (per child)')
    price_6pax_child = fields.Float(string='6 People (per child)')
    currency_id = fields.Many2one(related='package_id.currency_id')

    def get_price_display(self, amount):
        self.ensure_one()
        currency = self.currency_id
        amount_str = '%.0f' % amount
        if currency.position == 'before':
            return '%s%s' % (currency.symbol, amount_str)
        return '%s %s' % (amount_str, currency.symbol)

    def is_current(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return bool(self.date_start and self.date_end and self.date_start <= today <= self.date_end)
