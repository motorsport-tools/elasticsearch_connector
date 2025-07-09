import json
from odoo import models,fields,api
from odoo.fields import Field


class JSONField(Field):
    type = 'json'
    column_type = ('json', 'json')

    def __init__(self, string, **kwargs):
        self.column_type = ('json', 'json')

        super(JSONField, self).__init__(string= string, **kwargs)

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            return json.loads(value)
        return {}

    def convert_to_record(self, value, record):
        if value:
            return json.dumps(value)
        return value
