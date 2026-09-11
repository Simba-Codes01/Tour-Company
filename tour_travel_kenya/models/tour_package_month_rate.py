import calendar

from odoo import api, fields, models


class TourPackageMonthRate(models.Model):
    _name = 'tour.package.month.rate'
    _description = 'Tour Package Seasonal Rate'
    # Selection fields are stored as text, so ordering by 'month' directly would sort
    # '1', '10', '11', '12', '2', '3', ... alphabetically instead of calendar order.
    _order = 'month_number'

    package_id = fields.Many2one('tour.package', required=True, ondelete='cascade', index=True)
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], required=True)
    month_number = fields.Integer(compute='_compute_month_number', store=True)
    month_short = fields.Char(compute='_compute_month_short')
    currency_id = fields.Many2one(related='package_id.currency_id')
    price = fields.Float(string='Rate per Person Sharing', digits='Product Price', required=True)
    season = fields.Selection([
        ('low', 'Low Season'),
        ('mid', 'Shoulder Season'),
        ('peak', 'High Season'),
    ], default='mid', required=True)

    _package_month_uniq = models.Constraint(
        'unique(package_id, month)',
        'Only one rate can be set per month for a given package.',
    )

    @api.depends('month')
    def _compute_month_number(self):
        for rate in self:
            rate.month_number = int(rate.month) if rate.month else 0

    @api.depends('month')
    def _compute_month_short(self):
        for rate in self:
            rate.month_short = calendar.month_abbr[int(rate.month)].upper() if rate.month else ''
