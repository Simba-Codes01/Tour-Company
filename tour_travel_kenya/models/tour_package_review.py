from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TourPackageReview(models.Model):
    """A traveler review of a tour package.

    Anyone can submit one from the package page; it stays ``pending`` until
    staff publish it. Reviews left from a completed booking in the customer
    portal are published straight away and flagged as verified.
    """
    _name = 'tour.package.review'
    _description = 'Tour Package Review'
    _order = 'create_date desc, id desc'
    _rec_name = 'title'

    TRAVEL_TYPES = [
        ('solo', 'Solo'),
        ('couple', 'Couple'),
        ('family', 'Family'),
        ('friends', 'Friends'),
        ('business', 'Business'),
    ]

    package_id = fields.Many2one(
        'tour.package', string='Package', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='package_id.company_id', store=True)
    booking_id = fields.Many2one(
        'tour.booking', string='Booking', index='btree_not_null', ondelete='set null',
        help="Set when the review was left from a completed booking in the customer portal.")
    partner_id = fields.Many2one('res.partner', string='Customer', index='btree_not_null')
    author_name = fields.Char(string='Name', required=True)
    author_email = fields.Char(string='Email')
    rating = fields.Integer(string='Rating', required=True, default=5, aggregator='avg')
    title = fields.Char(string='Title')
    comment = fields.Text(string='Review', required=True)
    travel_type = fields.Selection(TRAVEL_TYPES, string='Traveled As')
    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', required=True, index=True)
    is_verified = fields.Boolean(
        string='Verified Traveler', compute='_compute_is_verified', store=True,
        help="The reviewer has a completed booking for this package.")
    helpful_count = fields.Integer(string='Helpful Votes', default=0, readonly=True)
    response = fields.Text(
        string='Our Response', help="Public reply from the team, shown under the review on the website.")
    published_date = fields.Datetime(string='Published On', readonly=True)
    public_author = fields.Char(compute='_compute_public_author', string='Shown As')
    author_initial = fields.Char(compute='_compute_public_author')

    _rating_range = models.Constraint(
        'CHECK(rating >= 1 AND rating <= 5)', 'The rating must be between 1 and 5 stars.')
    _booking_unique = models.UniqueIndex(
        '(booking_id) WHERE booking_id IS NOT NULL', 'A booking can only be reviewed once.')

    @api.depends('booking_id.state', 'partner_id', 'author_email', 'package_id')
    def _compute_is_verified(self):
        Booking = self.env['tour.booking'].sudo()
        for review in self:
            if review.booking_id:
                review.is_verified = review.booking_id.state == 'done'
                continue
            domain = [('package_id', '=', review.package_id.id), ('state', '=', 'done')]
            if review.partner_id:
                domain.append(('partner_id', '=', review.partner_id.id))
            elif review.author_email:
                domain.append(('email', '=ilike', review.author_email.strip()))
            else:
                review.is_verified = False
                continue
            review.is_verified = bool(review.package_id) and bool(Booking.search_count(domain, limit=1))

    @api.constrains('comment', 'author_name')
    def _check_lengths(self):
        for review in self:
            if len(review.comment or '') > 3000:
                raise ValidationError(_("Reviews are limited to 3000 characters."))
            if len(review.author_name or '') > 80:
                raise ValidationError(_("The name is too long."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('state') == 'published' and not vals.get('published_date'):
                vals['published_date'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('state') == 'published':
            to_stamp = self.filtered(lambda r: not r.published_date)
            if to_stamp:
                super(TourPackageReview, to_stamp).write({'published_date': fields.Datetime.now()})
        return super().write(vals)

    def action_publish(self):
        self.write({'state': 'published'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_pending(self):
        self.write({'state': 'pending'})

    @api.depends('author_name')
    def _compute_public_author(self):
        """First name + last initial, so full names aren't published."""
        for review in self:
            parts = (review.author_name or '').split()
            if not parts:
                review.public_author = _('Traveler')
            elif len(parts) == 1:
                review.public_author = parts[0]
            else:
                review.public_author = '%s %s.' % (parts[0], parts[-1][:1].upper())
            review.author_initial = (parts[0][:1].upper() if parts else 'T')
