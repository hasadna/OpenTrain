# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'StopTime'
        db.delete_table(u'timetable_stoptime')

        # Deleting model 'Stop'
        db.delete_table(u'timetable_stop')

        # Deleting model 'Trip'
        db.delete_table(u'timetable_trip')

        # Adding model 'TtTrip'
        db.create_table(u'timetable_tttrip', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trip_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('shape_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'timetable', ['TtTrip'])

        # Adding model 'TtStop'
        db.create_table(u'timetable_ttstop', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stop_id', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('stop_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('stop_lat', self.gf('django.db.models.fields.FloatField')()),
            ('stop_lon', self.gf('django.db.models.fields.FloatField')()),
            ('stop_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal(u'timetable', ['TtStop'])

        # Adding model 'TtStopTime'
        db.create_table(u'timetable_ttstoptime', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stop', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.TtStop'])),
            ('stop_sequence', self.gf('django.db.models.fields.IntegerField')()),
            ('exp_arrival', self.gf('django.db.models.fields.DateTimeField')()),
            ('exp_departure', self.gf('django.db.models.fields.DateTimeField')()),
            ('trip', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.TtTrip'])),
        ))
        db.send_create_signal(u'timetable', ['TtStopTime'])


    def backwards(self, orm):
        # Adding model 'StopTime'
        db.create_table(u'timetable_stoptime', (
            ('exp_departure', self.gf('django.db.models.fields.DateTimeField')()),
            ('stop', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.Stop'])),
            ('trip', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.Trip'])),
            ('exp_arrival', self.gf('django.db.models.fields.DateTimeField')()),
            ('stop_sequence', self.gf('django.db.models.fields.IntegerField')()),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'timetable', ['StopTime'])

        # Adding model 'Stop'
        db.create_table(u'timetable_stop', (
            ('stop_lat', self.gf('django.db.models.fields.FloatField')()),
            ('stop_lon', self.gf('django.db.models.fields.FloatField')()),
            ('stop_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('stop_id', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('stop_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'timetable', ['Stop'])

        # Adding model 'Trip'
        db.create_table(u'timetable_trip', (
            ('shape_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('trip_id', self.gf('django.db.models.fields.CharField')(max_length=100, unique=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'timetable', ['Trip'])

        # Deleting model 'TtTrip'
        db.delete_table(u'timetable_tttrip')

        # Deleting model 'TtStop'
        db.delete_table(u'timetable_ttstop')

        # Deleting model 'TtStopTime'
        db.delete_table(u'timetable_ttstoptime')


    models = {
        u'timetable.ttstop': {
            'Meta': {'object_name': 'TtStop'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stop_lat': ('django.db.models.fields.FloatField', [], {}),
            'stop_lon': ('django.db.models.fields.FloatField', [], {}),
            'stop_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'stop_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        u'timetable.ttstoptime': {
            'Meta': {'object_name': 'TtStopTime'},
            'exp_arrival': ('django.db.models.fields.DateTimeField', [], {}),
            'exp_departure': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.TtStop']"}),
            'stop_sequence': ('django.db.models.fields.IntegerField', [], {}),
            'trip': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.TtTrip']"})
        },
        u'timetable.tttrip': {
            'Meta': {'object_name': 'TtTrip'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'shape_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'trip_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        }
    }

    complete_apps = ['timetable']