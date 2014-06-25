# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StopTime'
        db.create_table(u'timetable_stoptime', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stop', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.Stop'])),
            ('stop_sequence', self.gf('django.db.models.fields.IntegerField')()),
            ('exp_arrival', self.gf('django.db.models.fields.DateTimeField')()),
            ('exp_departure', self.gf('django.db.models.fields.DateTimeField')()),
            ('trip', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.Trip'])),
        ))
        db.send_create_signal(u'timetable', ['StopTime'])

        # Adding model 'Trip'
        db.create_table(u'timetable_trip', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trip_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('shape_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'timetable', ['Trip'])


    def backwards(self, orm):
        # Deleting model 'StopTime'
        db.delete_table(u'timetable_stoptime')

        # Deleting model 'Trip'
        db.delete_table(u'timetable_trip')


    models = {
        u'timetable.stop': {
            'Meta': {'object_name': 'Stop'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stop_lat': ('django.db.models.fields.FloatField', [], {}),
            'stop_lon': ('django.db.models.fields.FloatField', [], {}),
            'stop_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'stop_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        u'timetable.stoptime': {
            'Meta': {'object_name': 'StopTime'},
            'exp_arrival': ('django.db.models.fields.DateTimeField', [], {}),
            'exp_departure': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.Stop']"}),
            'stop_sequence': ('django.db.models.fields.IntegerField', [], {}),
            'trip': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.Trip']"})
        },
        u'timetable.trip': {
            'Meta': {'object_name': 'Trip'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'shape_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'trip_id': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['timetable']