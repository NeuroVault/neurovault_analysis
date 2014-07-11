from pandas.io.json import json_normalize
from urllib2 import Request, urlopen
import pandas as pd
import json

def get_collections_df():
    """Downloads metadata about collections/papers stored in NeuroVault and 
    return it as a pandas DataFrame"""
    
    request=Request('http://neurovault.org/api/collections/?format=json')
    response = urlopen(request)
    elevations = response.read()
    data = json.loads(elevations)
    collections_df = json_normalize(data)
    collections_df.rename(columns={'id':'collection_id'}, inplace=True)
    collections_df.set_index("collection_id")
    
    return collections_df

def get_images_df():
    """Downloads metadata about images/statistical maps stored in NeuroVault and 
    return it as a pandas DataFrame"""

    request=Request('http://neurovault.org/api/images/?format=json')
    response = urlopen(request)
    elevations = response.read()
    data = json.loads(elevations)
    images_df = json_normalize(data)
    images_df['collection'] = images_df['collection'].apply(lambda x: int(x.split("/")[-2]))
    images_df.rename(columns={'collection':'collection_id'}, inplace=True)
    return images_df

def get_images_with_collections_df():
    """Downloads metadata about images/statistical maps stored in NeuroVault and
    and enriches it with metadata of the corresponding collections. The result 
    is returned as a pandas DataFrame"""
    
    collections_df = get_collections_df()
    images_df = get_images_df()

    combined_df = pd.merge(images_df, collections_df, how='left', on='collection_id',
                      suffixes=('_image', '_collection'))
    return combined_df


if __name__ == '__main__':
    combined_df = get_images_with_collections_df()
    print combined_df[['DOI', 'url_collection', 'name_image', 'file']]
