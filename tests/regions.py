from itools.cms.csv import CSV
from itools.handlers import get_handler
from itools.datatypes import Integer, String, Unicode
from itools import get_abspath
from itools.handlers import get_handler
from abakuc.root import world
path = get_abspath(globals(), '/Users/khinester/Desktop/oracle/world_regions.csv')
columns = ['country', 'id','region', 'county']
schema = {'country': String, 'id': String, 'region': Unicode, 'county': Unicode}
countries = get_handler(path)

#rows = world.get_rows()
#regions = countries.get_rows()
## List countries and its regions
#xx = []
#for row in rows:
#    country = row.get_value('country')
#    region = row.get_value('region')
#    if region and (region==u'none'):
#        for province in regions:
#            p_country = row.get_value('country')
#            if country == p_country:
#                xx.append(province)
#print xx

for row in countries.get_rows():
    country, id,region, county = row
    print id
    #name = country[0]
    #results = world.search(country=name)
    #print results

#countries
#code = []               
#for row in countries.get_rows():
#    code.append(row[0])
#province = []
#
#print code
