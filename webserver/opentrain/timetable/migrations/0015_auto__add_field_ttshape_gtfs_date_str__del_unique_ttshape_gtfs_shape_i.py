# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'TtShape', fields ['gtfs_shape_id']
        db.delete_unique(u'timetable_ttshape', ['gtfs_shape_id'])

        # Adding field 'TtShape.gtfs_date_str'
        db.add_column(u'timetable_ttshape', 'gtfs_date_str',
                      self.gf('django.db.models.fields.CharField')(default='2014_dummy', max_length=20),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'TtShape.gtfs_date_str'
        db.delete_column(u'timetable_ttshape', 'gtfs_date_str')

        # Adding unique constraint on 'TtShape', fields ['gtfs_shape_id']
        db.create_unique(u'timetable_ttshape', ['gtfs_shape_id'])


    models = {
        u'timetable.ttshape': {
            'Meta': {'object_name': 'TtShape'},
            'gtfs_date_str': ('django.db.models.fields.CharField', [], {'default': "'2014_dummy'", 'max_length': '20'}),
            'gtfs_shape_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
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