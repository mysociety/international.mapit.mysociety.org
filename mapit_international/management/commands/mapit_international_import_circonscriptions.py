from collections import defaultdict

from django.contrib.gis.gdal import DataSource
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.functional import cached_property

from mapit.management.command_utils import save_polygons
from mapit.models import Area, CodeType, Country, Type


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
            'GEOJSON-FILENAME',
            help='The circonscriptions legislatives GeoJSON filename')

    @cached_property
    def country(self):
        return Country.objects.get(code='FR')

    @cached_property
    def area_type(self):
        return Type.objects.get(code='FRCIR')

    @cached_property
    def code_type(self):
        return CodeType.objects.get(code='ref-cir')

    def update_area(self, ref, polygons):
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
            codes__code=ref,
            defaults={
                'name': ref,
                'generation_low_id': self.generation_id,
                'generation_high_id': self.generation_id,
            })
        if created:
            # Then it won't have the right code object yet:
            area.codes.update_or_create(
                type=self.code_type,
                defaults={'code': ref})
        # Now update the polygons associated with that area:
        save_polygons({None: (area, [unioned])})

    def handle(self, **options):
        self.generation_id = options['generation_id']
        if not self.generation_id:
            raise CommandError('No generation ID supplied')
        ds = DataSource(options['GEOJSON-FILENAME'])
        ref_to_polygons = defaultdict(list)
        layer = ds[0]
        with transaction.atomic():
            for feature in layer:
                ref = unicode(feature['REF'])
                ref_to_polygons[ref].append(feature.geom)
            for ref, polygons in ref_to_polygons.items():
                self.update_area(ref, polygons)
