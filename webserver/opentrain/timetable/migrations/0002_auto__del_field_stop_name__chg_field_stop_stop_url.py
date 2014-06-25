# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Stop.name'
        db.delete_column(u'timetable_stop', 'name')


        # Changing field 'Stop.stop_url'
        db.alter_column(u'timetable_stop', 'stop_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Stop.name'
        raise RuntimeError("Cannot reverse this migration. 'Stop.name' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Stop.name'
        db.add_column(u'timetable_stop', 'name',
                      self.gf('django.db.models.fields.CharField')(max_length=100),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Stop.stop_url'
        raise RuntimeError("Cannot reverse this migration. 'Stop.stop_url' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Stop.stop_url'
        db.alter_column(u'timetable_stop', 'stop_url', self.gf('django.db.models.fields.URLField')(max_length=200))

    models = {
        u'timetable.stop': {
            'Meta': {'object_name': 'Stop'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stop_lat': ('django.db.models.fields.FloatField', [], {}),
            'stop_lon': ('django.db.models.fields.FloatField', [], {}),
            'stop_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'stop_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['timetable']