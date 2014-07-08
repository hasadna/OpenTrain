# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RtStop'
        db.create_table(u'analysis_rtstop', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('tracker_id', self.gf('django.db.models.fields.CharField')(max_length=40, db_index=True)),
            ('trip', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.TtTrip'])),
            ('stop', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timetable.TtStop'])),
            ('act_arrival', self.gf('django.db.models.fields.DateTimeField')()),
            ('act_departure', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'analysis', ['RtStop'])

        # Adding unique constraint on 'RtStop', fields ['tracker_id', 'trip', 'stop']
        db.create_unique(u'analysis_rtstop', ['tracker_id', 'trip_id', 'stop_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'RtStop', fields ['tracker_id', 'trip', 'stop']
        db.delete_unique(u'analysis_rtstop', ['tracker_id', 'trip_id', 'stop_id'])

        # Deleting model 'RtStop'
        db.delete_table(u'analysis_rtstop')


    models = {
        u'analysis.locationinfo': {
            'Meta': {'object_name': 'LocationInfo'},
            'accuracy': ('django.db.models.fields.FloatField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lon': ('django.db.models.fields.FloatField', [], {}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'report': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'my_loc'", 'unique': 'True', 'to': u"orm['analysis.Report']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'analysis.report': {
            'Meta': {'object_name': 'Report'},
            'app_version_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '20'}),
            'app_version_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'device_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'analysis.rtstop': {
            'Meta': {'unique_together': "(('tracker_id', 'trip', 'stop'),)", 'object_name': 'RtStop'},
            'act_arrival': ('django.db.models.fields.DateTimeField', [], {}),
            'act_departure': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.TtStop']"}),
            'tracker_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'trip': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['timetable.TtTrip']"})
        },
        u'analysis.singlewifireport': {
            'Meta': {'object_name': 'SingleWifiReport'},
            'SSID': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'frequency': ('django.db.models.fields.FloatField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wifi_set'", 'to': u"orm['analysis.Report']"}),
            'signal': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
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

    complete_apps = ['analysis']