# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'RawReport', fields ['saved_at']
        db.create_index(u'reports_rawreport', ['saved_at'])


    def backwards(self, orm):
        # Removing index on 'RawReport', fields ['saved_at']
        db.delete_index(u'reports_rawreport', ['saved_at'])


    models = {
        u'reports.rawreport': {
            'Meta': {'object_name': 'RawReport'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'saved_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['reports']