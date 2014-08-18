from pandas.io.json import json_normalize
from urllib2 import Request, urlopen
import pandas as pd
import nibabel as nb
import numpy as np
import pylab as plt
import json
import urllib, os, errno
from nipype.utils.filemanip import split_filename

from joblib import Memory

from nilearn.image import resample_img
from nilearn.plotting.img_plotting import plot_stat_map


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def get_collections_df():
    """Downloads metadata about collections/papers stored in NeuroVault and
    return it as a pandas DataFrame"""
    
    request = Request('http://neurovault.org/api/collections/?format=json')
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
    images_df['image_id'] = images_df['url'].apply(lambda x: int(x.split("/")[-2]))
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


def download_and_resample(images_df, dest_dir, target):
    """Downloads all stat maps and resamples them to a common space.
    """

    target_nii = nb.load(target)
    orig_path = os.path.join(dest_dir, "original")
    mkdir_p(orig_path)
    resampled_path = os.path.join(dest_dir, "resampled")
    mkdir_p(resampled_path)
    out_df = combined_df.copy()

    for row in combined_df.iterrows():
        # Downloading the file to the "original" subfolder
        _, _, ext = split_filename(row[1]['file'])
        orig_file = os.path.join(orig_path, "%04d%s" % (row[1]['image_id'], ext))
        if not os.path.exists(orig_file):
            print "Downloading %s" % orig_file
            urllib.urlretrieve(row[1]['file'], orig_file)

        # Resampling the file to target and saving the output in the "resampled"
        # folder
        resampled_file = os.path.join(resampled_path,
                                      "%06d%s" % (row[1]['image_id'], ext))

        print "Resampling %s" % orig_file
        resampled_nii = resample_img(orig_file, target_nii.get_affine(),
            target_nii.shape)
        resampled_nii = nb.Nifti1Image(resampled_nii.get_data().squeeze(),
                                        resampled_nii.get_affine())
        if len(resampled_nii.shape) == 3:
            resampled_nii.to_filename(resampled_file)
        else:
            # We have a 4D file
            assert len(resampled_nii.shape) == 4
            resampled_data = resampled_nii.get_data()
            affine = resampled_nii.affine
            for index in range(resampled_nii.shape[-1]):

                # First save the files separately
                this_nii = nb.Nifti1Image(resampled_data[..., index],
                                            affine)
                this_id = int("%i%i" % (-row[1]['image_id'], index))
                this_file = os.path.join(resampled_path,
                    "%06d%s" % (this_id, ext))
                this_nii.to_filename(this_file)

                # Second, fix the dataframe
                out_df = out_df[out_df.image_id != row[1]['image_id']]
                this_row = row[1].copy()
                this_row.image_id = this_id
                out_df = out_df.append(this_row)

    return out_df


def get_frequency_map(images_df, dest_dir, target):
    """
    """
    mask_img = 'gm_mask.nii.gz'
    mask = nb.load(mask_img).get_data().astype(np.bool)


    target_nii = nb.load(target)
    orig_path = os.path.join(dest_dir, "original")
    resampled_path = os.path.join(dest_dir, "resampled")
    freq_map_data = np.zeros(target_nii.shape)
    mean_map_data = np.zeros(target_nii.shape)

    for row in combined_df.iterrows():
        _, _, ext = split_filename(row[1]['file'])
        orig_file = os.path.join(resampled_path, "%06d%s" % (row[1]['image_id'], ext))
        nb.load(orig_file)
        if not os.path.exists(orig_file):
            urllib.urlretrieve(row[1]['file'], orig_file)

        resampled_nii = resample_img(orig_file, target_nii.get_affine(),
                                     target_nii.shape,
                                     interpolation="nearest")
        data = resampled_nii.get_data().squeeze()
        data[np.isnan(data)] = 0
        data[np.logical_not(mask)] = 0
        data = np.abs(data)
        # Put things that are severely not significant to 0
        data[data < 1] = 0
        if len(data.shape) == 4:
            for d in np.rollaxis(data, -1):
                mean_map_data += d
        else:
            mean_map_data += data

        # Keep only things that are very significant
        data = data > 3
        if len(data.shape) == 4:
            for d in np.rollaxis(data, -1):
                freq_map_data += d
        else:
            freq_map_data += data


    return (nb.Nifti1Image(freq_map_data, target_nii.get_affine()),
            nb.Nifti1Image(mean_map_data, target_nii.get_affine()))


if __name__ == '__main__':
    # Use a joblib memory, to avoid depending on an Internet connection
    mem = Memory(cachedir='/tmp/neurovault_analysis/cache')
    combined_df = mem.cache(get_images_with_collections_df)()

    # The following maps are not brain maps
    faulty_ids = [96, 97, 98]
    # And the following are crap
    faulty_ids.extend([338, 339])
    combined_df = combined_df[~combined_df.image_id.isin(faulty_ids)]

    # Collection 78 is very different from the rest of the data, and
    # seems to be a first-level analysis
    faulty_collections = [78, ]
    combined_df = combined_df[
            ~combined_df.collection_id.isin(faulty_collections)]


    print combined_df[['DOI', 'url_collection', 'name_image', 'file']]

    #restrict to Z-, F-, or T-maps
    combined_df = combined_df[combined_df['map_type'].isin(["Z","F","T"])]
    print combined_df["name_collection"].value_counts()

    dest_dir = "/tmp/neurovault_analysis"
    target = "/usr/share/fsl/data/standard/MNI152_T1_2mm.nii.gz"

    combined_df = mem.cache(download_and_resample)(combined_df,
                                                   dest_dir, target)

    freq_nii, mean_nii = get_frequency_map(combined_df, dest_dir, target)
    freq_nii.to_filename("/tmp/freq_map.nii.gz")
    mean_nii.to_filename("/tmp/mean_map.nii.gz")

    plot_stat_map(freq_nii, "/usr/share/fsl/data/standard/MNI152_T1_2mm.nii.gz",
                  display_mode="z")
    plot_stat_map(mean_nii, "/usr/share/fsl/data/standard/MNI152_T1_2mm.nii.gz",
                  display_mode="z")
    plt.show()
        
    combined_df.to_csv('%s/metadata.csv' % dest_dir, encoding='utf8')
