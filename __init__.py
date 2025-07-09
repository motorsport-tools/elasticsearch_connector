from . import models


def pre_init_check(cr):

    # Odoo Module
    from odoo.service import common
    from odoo.exceptions import ValidationError
    from odoo import _

    version_info = common.exp_version()
    server_serie = version_info.get('server_serie')
    if server_serie != '17.0':
    	raise ValidationError(_('This module is for Odoo v17.0 {}.'.format(server_serie)))