# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Stop'
        db.create_table(u'timetable_stop', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('stop_id', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('stop_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('stop_lat', self.gf('django.db.models.fields.FloatField')()),
            ('stop_lon', self.gf('django.db.models.fields.FloatField')()),
            ('stop_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal(u'timetable', ['Stop'])


    def backwards(self, orm):
        # Deleting model 'Stop'
        db.delete_table(u'timetable_stop')


    models = {
        u'timetable.stop': {
            'Meta': {'object_name': 'Stop'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'stop_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stop_lat': ('django.db.models.fields.FloatField', [], {}),
            'stop_lon': ('django.db.models.fields.FloatField', [], {}),
            'stop_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'stop_url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['timetable']