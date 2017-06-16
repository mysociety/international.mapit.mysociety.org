# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from collections import defaultdict
import re

from django.contrib.gis.gdal import DataSource
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.functional import cached_property

from mapit.management.command_utils import save_polygons
from mapit.models import Area, CodeType, Country, Generation, Type


DEPARTMENT_TO_EUR = {
    '43': 'massif-central-centre',
    '63': 'massif-central-centre',
    '12': 'sud-ouest',
    '48': 'sud-ouest',
    '81': 'sud-ouest',
    '24': 'sud-ouest',
    '32': 'sud-ouest',
    '47': 'sud-ouest',
    '82': 'sud-ouest',
    '46': 'sud-ouest',
    '19': 'massif-central-centre',
    '87': 'massif-central-centre',
    '16': 'ouest',
    '50': 'nord-ouest',
    '53': 'ouest',
    '27': 'nord-ouest',
    '72': 'ouest',
    '76': 'nord-ouest',
    '14': 'nord-ouest',
    '61': 'nord-ouest',
    '59': 'nord-ouest',
    '2': 'nord-ouest',
    '80': 'nord-ouest',
    '62': 'nord-ouest',
    '60': 'nord-ouest',
    '8': 'est',
    '67': 'est',
    '52': 'est',
    '10': 'est',
    '68': 'est',
    '54': 'est',
    '57': 'est',
    '55': 'est',
    '51': 'est',
    '84': 'sud-est',
    '69D': 'sud-est',
    '1': 'sud-est',
    '3': 'massif-central-centre',
    '15': 'massif-central-centre',
    '7': 'sud-est',
    '23': 'massif-central-centre',
    '70': 'est',
    '25': 'est',
    '21': 'est',
    '88': 'est',
    '90': 'est',
    '89': 'est',
    '58': 'est',
    '41': 'massif-central-centre',
    '93': 'ile-de-france',
    '37': 'massif-central-centre',
    '91': 'ile-de-france',
    '28': 'massif-central-centre',
    '18': 'massif-central-centre',
    '49': 'ouest',
    '44': 'ouest',
    '34': 'sud-ouest',
    '31': 'sud-ouest',
    '35': 'ouest',
    '42': 'sud-est',
    '30': 'sud-ouest',
    '86': 'ouest',
    '95': 'ile-de-france',
    '77': 'ile-de-france',
    '45': 'massif-central-centre',
    '78': 'ile-de-france',
    '94': 'ile-de-france',
    '33': 'sud-ouest',
    '40': 'sud-ouest',
    '69M': 'sud-est',
    '38': 'sud-est',
    '71': 'est',
    '36': 'massif-central-centre',
    '79': 'ouest',
    '65': 'sud-ouest',
    '75': 'ile-de-france',
    '92': 'ile-de-france',
    '11': 'sud-ouest',
    '66': 'sud-ouest',
    '17': 'ouest',
    '64': 'sud-ouest',
    '39': 'est',
    '73': 'sud-est',
    '5': 'sud-est',
    '74': 'sud-est',
    '85': 'ouest',
    '973': 'outre-mer',
    '971': 'outre-mer',
    '972': 'outre-mer',
    '56': 'ouest',
    '22': 'ouest',
    '29': 'ouest',
    '9': 'sud-ouest',
    '2B': 'sud-est',
    '2A': 'sud-est',
    '26': 'sud-est',
    '83': 'sud-est',
    '4': 'sud-est',
    '974': 'outre-mer',
    '13': 'sud-est',
    '6': 'sud-est',
    '976': 'outre-mer',
}


EUR_ID_TO_NAME = {
    'est': u'Est',
    'ile-de-france': u'Île-de-France',
    'massif-central-centre': u'Massif Central-Centre',
    'nord-ouest': u'Nord-Ouest',
    'ouest': u'Ouest',
    'outre-mer': u'Outre-Mer',
    'sud-est': u'Sud-Est',
    'sud-ouest': u'Sud-Ouest',
}


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        )
        parser.add_argument(
            '--generation_id',
            action="store",
            dest='generation_id',
            help='Which generation ID should be used',
        )
        parser.add_argument(
            'DEPARTMENT-FILENAME',
            help='The departements Shapefile filename')

    @cached_property
    def country(self):
        return Country.objects.get(code='FR')

    @cached_property
    def area_type(self):
        return Type.objects.get_or_create(
            code='FREUR',
            defaults={
                'description':
                'French European Parliament constituency',
            })[0]

    @cached_property
    def code_type(self):
        return CodeType.objects.get_or_create(
            code='eur',
            defaults={
                'description':
                'Slug of French European Parliament constituency name',
            })[0]

    def update_area(self, eur_id, polygons):
        area_name = EUR_ID_TO_NAME[eur_id]
        unioned = polygons[0]
        for polygon in polygons[1:]:
            unioned = unioned.union(polygon)
            # Now make sure the area object exists:
        area, created = Area.objects.get_or_create(
            country=self.country,
            type=self.area_type,
            generation_low__lte=self.generation_id,
            generation_high__gte=self.generation_id,
            codes__type=self.code_type,
            codes__code=eur_id,
            defaults={
                'name': area_name,
                'generation_low_id': self.generation_id,
                'generation_high_id': self.generation_id,
            })
        if created:
            # Then it won't have the right code object yet:
            area.codes.update_or_create(
                type=self.code_type,
                defaults={'code': eur_id})
        # Now update the polygons associated with that area:
        save_polygons({None: (area, [unioned])})

    def handle(self, **options):
        self.generation_id = options['generation_id']
        if not self.generation_id:
            raise CommandError('No generation ID supplied')
        ds = DataSource(options['DEPARTMENT-FILENAME'])
        eur_id_to_polygons = defaultdict(list)
        layer = ds[0]
        with transaction.atomic():
            for feature in layer:
                insee_code = unicode(feature['code_insee'])
                code_key = re.sub(r'^0*', '', insee_code)
                eur_id = DEPARTMENT_TO_EUR[code_key]
                eur_id_to_polygons[eur_id].append(feature.geom)
            for eur_id, polygons in eur_id_to_polygons.items():
                self.update_area(eur_id, polygons)
