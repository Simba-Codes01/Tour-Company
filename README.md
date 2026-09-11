# Tour Company — Odoo Custom Addons

Custom Odoo 19.0 modules for [describe your business/client here].

## Modules

### payment_mpesa
M-Pesa payment provider integration for Odoo — adds M-Pesa as a payment method and handles payment transactions.

### tour_travel_kenya
Tour and travel booking module for managing tour packages, bookings, pricing, and related operations.

## Setup

1. Clone this repo into your Odoo custom addons path.
2. Add the path to \ddons_path\ in your \odoo.conf\:
   \\\
   addons_path = C:\path\to\odoo-19.0\addons,C:\path\to\custom-addons
   \\\
3. Restart the Odoo service.
4. Activate developer mode in Odoo, go to Apps, update the apps list, and install the modules.

## Requirements

- Odoo 19.0
- (List any Python package dependencies here, e.g. from requirements.txt in each module)
