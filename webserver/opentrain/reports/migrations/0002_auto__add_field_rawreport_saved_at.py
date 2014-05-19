# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'RawReport.saved_at'
        db.add_column(u'reports_rawreport', 'saved_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 10, 31, 0, 0), auto_now_add=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'RawReport.saved_at'
        db.delete_column(u'reports_rawreport', 'saved_at')


    models = {
        u'reports.rawreport': {
            'Meta': {'object_name': 'RawReport'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'saved_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 10, 31, 0, 0)', 'auto_now_add': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['reports']