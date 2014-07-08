# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'RealTimeStop', fields ['tracker_id', 'trip', 'stop']
        db.delete_unique(u'analysis_realtimestop', ['tracker_id', 'trip_id', 'stop_id'])

        # Deleting model 'RealTimeStop'
        db.delete_table(u'analysis_realtimestop')


    def backwards(self, orm):
        # Adding model 'RealTimeStop'
        db.create_table(u'analysis_realtimestop', (
            ('stop', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gtfs.Stop'])),
            ('tracker_id', self.gf('django.db.models.fields.CharField')(max_length=40, db_index=True)),
            ('trip', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gtfs.Trip'])),
            ('arrival_time', self.gf('django.db.models.fields.DateTimeField')()),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('departure_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'analysis', ['RealTimeStop'])

        # Adding unique constraint on 'RealTimeStop', fields ['tracker_id', 'trip', 'stop']
        db.create_unique(u'analysis_realtimestop', ['tracker_id', 'trip_id', 'stop_id'])


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
        u'analysis.singlewifireport': {
            'Meta': {'object_name': 'SingleWifiReport'},
            'SSID': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'frequency': ('django.db.models.fields.FloatField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wifi_set'", 'to': u"orm['analysis.Report']"}),
            'signal': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['analysis']