# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'TtTrip.from_stoptime'
        db.add_column(u'timetable_tttrip', 'from_stoptime',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='first_stop', null=True, to=orm['timetable.TtStopTime']),
                      keep_default=False)

        # Adding field 'TtTrip.to_stoptime'
        db.add_column(u'timetable_tttrip', 'to_stoptime',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='last_stop', null=True, to=orm['timetable.TtStopTime']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TtTrip.from_stoptime'
        db.delete_column(u'timetable_tttrip', 'from_stoptime_id')

        # Deleting field 'TtTrip.to_stoptime'
        db.delete_column(u'timetable_tttrip', 'to_stoptime_id')


    models = {
        u'timetable.ttshape': {
            'Meta': {'object_name': 'TtShape'},
            'gtfs_shape_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.TextField', [], {})
        },
        u'timetable.ttstop': {
            'Meta': {'object_name': 'TtStop'},
            'gtfs_stop_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'from_stoptime': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'first_stop'", 'null': 'True', 'to': u"orm['timetable.TtStopTime']"}),
            'gtfs_trip_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'shape': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.TtShape']", 'null': 'True'}),
            'to_stoptime': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'last_stop'", 'null': 'True', 'to': u"orm['timetable.TtStopTime']"})
        }
    }

    complete_apps = ['timetable']