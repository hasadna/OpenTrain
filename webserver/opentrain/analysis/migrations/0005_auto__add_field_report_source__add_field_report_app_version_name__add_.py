# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Report.source'
        db.add_column(u'analysis_report', 'source',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=30),
                      keep_default=False)

        # Adding field 'Report.app_version_name'
        db.add_column(u'analysis_report', 'app_version_name',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=30),
                      keep_default=False)

        # Adding field 'Report.app_version_code'
        db.add_column(u'analysis_report', 'app_version_code',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=20),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Report.source'
        db.delete_column(u'analysis_report', 'source')

        # Deleting field 'Report.app_version_name'
        db.delete_column(u'analysis_report', 'app_version_name')

        # Deleting field 'Report.app_version_code'
        db.delete_column(u'analysis_report', 'app_version_code')


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
        u'analysis.realtimestop': {
            'Meta': {'unique_together': "(('tracker_id', 'trip', 'stop'),)", 'object_name': 'RealTimeStop'},
            'arrival_time': ('django.db.models.fields.DateTimeField', [], {}),
            'departure_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stop': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gtfs.Stop']"}),
            'tracker_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'trip': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gtfs.Trip']"})
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
        u'analysis.singlewifireport': {
            'Meta': {'object_name': 'SingleWifiReport'},
            'SSID': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'frequency': ('django.db.models.fields.FloatField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wifi_set'", 'to': u"orm['analysis.Report']"}),
            'signal': ('django.db.models.fields.IntegerField', [], {})
        },
        u'gtfs.agency': {
            'Meta': {'object_name': 'Agency'},
            'agency_id': ('django.db.models.fields.IntegerField', [], {'default': '1', 'max_length': '255', 'primary_key': 'True'}),
            'agency_lang': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'agency_name': ('django.db.models.fields.TextField', [], {}),
            'agency_timezone': ('django.db.models.fields.TextField', [], {}),
            'agency_url': ('django.db.models.fields.TextField', [], {})
        },
        u'gtfs.route': {
            'Meta': {'object_name': 'Route'},
            'agency': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gtfs.Agency']", 'null': 'True', 'blank': 'True'}),
            'route_color': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'route_desc': ('django.db.models.fields.TextField', [], {}),
            'route_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'route_long_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'route_short_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'route_text_color': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'route_type': ('django.db.models.fields.IntegerField', [], {})
        },
        u'gtfs.service': {
            'Meta': {'object_name': 'Service'},
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'friday': ('django.db.models.fields.BooleanField', [], {}),
            'monday': ('django.db.models.fields.BooleanField', [], {}),
            'saturday': ('django.db.models.fields.BooleanField', [], {}),
            'service_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'sunday': ('django.db.models.fields.BooleanField', [], {}),
            'thursday': ('django.db.models.fields.BooleanField', [], {}),
            'tuesday': ('django.db.models.fields.BooleanField', [], {}),
            'wednesday': ('django.db.models.fields.BooleanField', [], {})
        },
        u'gtfs.stop': {
            'Meta': {'object_name': 'Stop'},
            'location_type': ('django.db.models.fields.IntegerField', [], {}),
            'stop_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'stop_lat': ('django.db.models.fields.FloatField', [], {}),
            'stop_lon': ('django.db.models.fields.FloatField', [], {}),
            'stop_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'stop_url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'gtfs.trip': {
            'Meta': {'object_name': 'Trip'},
            'direction_id': ('django.db.models.fields.IntegerField', [], {}),
            'route': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gtfs.Route']"}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gtfs.Service']"}),
            'shape_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'trip_headsign': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'trip_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'}),
            'wheelchair_accessible': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['analysis']