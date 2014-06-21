import csv
def read_csv(filename):
    with open(filename) as fh:
        result = []
        reader = csv.DictReader(fh, delimiter=',')
        for row in reader:
            d = dict()
            for key,value in row.iteritems():
                key_decoded = key.decode('utf-8-sig')
                value_decoded = value.decode('utf-8-sig')
                d[key_decoded] = value_decoded
            result.append(d)
        return result
                
        
def build_stops():
    stops = read_csv('stops.txt')
    
    