# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'TrainData'
        db.delete_table(u'traindata_traindata')


    def backwards(self, orm):
        # Adding model 'TrainData'
        db.create_table(u'traindata_traindata', (
            ('raw_stop_id', self.gf('django.db.models.fields.IntegerField')()),
            ('stop', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['gtfs.Stop'], null=True, blank=True)),
            ('exp_arrival', self.gf('django.db.models.fields.IntegerField')()),
            ('actual_arrival', self.gf('django.db.models.fields.IntegerField')()),
            ('date', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('file', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('raw_stop_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('line', self.gf('django.db.models.fields.IntegerField')()),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('exp_departure', self.gf('django.db.models.fields.IntegerField')()),
            ('actual_departure', self.gf('django.db.models.fields.IntegerField')()),
            ('train_num', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'traindata', ['TrainData'])


    models = {
        
    }

    complete_apps = ['traindata']