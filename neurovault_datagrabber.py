""" Code to grab the data from NeuroVault, and compute a map of
frequency of activation in the brain.
"""
# Authors: Chris Filo Gorgolewski, Gael Varoquaux
# License: BSD

import json
import urllib, os, errno
from urllib2 import Request, urlopen, HTTPError

import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import pylab as plt

from nipype.utils.filemanip import split_filename
import nibabel as nb

from joblib import Memory

from nilearn.image import resample_img
from nilearn.masking import compute_background_mask, _extrapolate_out_mask
from nilearn.plotting.img_plotting import plot_anat

# Use a joblib memory, to avoid depending on an Internet connection
mem = Memory(cachedir='/tmp/neurovault_analysis/cache')


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

        try:
            # Compute the background and extrapolate outside of the mask
            print "Extrapolating %s" % orig_file
            niimg = nb.load(orig_file)
            data = niimg.get_data().squeeze()
            niimg = nb.Nifti1Image(data, niimg.affine,
                                header=niimg.get_header())
            bg_mask = compute_background_mask(niimg).get_data()
            # Test if the image has been masked:
            out_of_mask = data[np.logical_not(bg_mask)]
            if np.all(np.isnan(out_of_mask)) or len(np.unique(out_of_mask)) == 1:
                # Need to extrapolate
                data = _extrapolate_out_mask(data.astype(np.float), bg_mask,
                                            iterations=3)[0]
            niimg = nb.Nifti1Image(data, niimg.affine,
                                header=niimg.get_header())
            del out_of_mask, bg_mask
            # Resampling the file to target and saving the output in the "resampled"
            # folder
            resampled_file = os.path.join(resampled_path,
                                        "%06d%s" % (row[1]['image_id'], ext))

            print "Resampling %s" % orig_file
            resampled_nii = resample_img(niimg, target_nii.get_affine(),
                target_nii.shape)
            resampled_nii = nb.Nifti1Image(resampled_nii.get_data().squeeze(),
                                        resampled_nii.get_affine(),
                                        header=niimg.get_header())
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
        except IOError as e:
            # Fix the dataframe
            out_df = out_df[out_df.image_id != row[1]['image_id']]
            print "Could not load %s " % orig_file
            print e

    return out_df


def get_frequency_map(images_df, dest_dir, target):
    """
    """
    mask_img = 'gm_mask.nii.gz'
    mask = nb.load(mask_img).get_data().astype(np.bool)


    target_nii = nb.load(target)
    resampled_path = os.path.join(dest_dir, "resampled")
    freq_map_data = np.zeros(target_nii.shape)

    n_images = 0
    for row in combined_df.iterrows():
        _, _, ext = split_filename(row[1]['file'])
        orig_file = os.path.join(resampled_path,
                                 "%06d%s" % (row[1]['image_id'], ext))
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

        # Keep only things that are very significant
        data = data > 3
        if len(data.shape) == 4:
            for d in np.rollaxis(data, -1):
                freq_map_data += (d != 0)
                n_images +=1
        else:
            freq_map_data += data
            n_images += 1

    freq_map_data *= 100. / n_images

    return nb.Nifti1Image(freq_map_data, target_nii.get_affine())


def url_get(url):
    request = Request(url)
    response = urlopen(request)
    return response.read()


def get_neurosynth_terms(combined_df):
    """ Grab terms for each image, decoded with neurosynth"""
    terms = list()
    from sklearn.feature_extraction import DictVectorizer
    vectorizer = DictVectorizer()
    image_ids = list()
    for row in combined_df.iterrows():
        image_id = row[1]['image_id']
        image_ids.append(int(image_id))
        print "Fetching terms for image %i" % image_id
        image_url = row[1]['url_image'].split('/')[-2]

        try:
            elevations = mem.cache(url_get)(
                        'http://neurosynth.org/decode/data/?neurovault=%s'
                        % image_url)
            data = json.loads(elevations)['data']
            data = dict([(i['analysis'], i['r']) for i in data])
        except HTTPError:
            data = {}
        terms.append(data)
    X = vectorizer.fit_transform(terms).toarray()
    term_dframe = dict([('neurosynth decoding %s' % name, X[:, idx])
                        for name, idx in vectorizer.vocabulary_.items()])
    term_dframe['image_id'] = image_ids

    return pd.DataFrame(term_dframe)




if __name__ == '__main__':
    #mem.clear()
    combined_df = mem.cache(get_images_with_collections_df)()

    # The following maps are not brain maps
    faulty_ids = [96, 97, 98]
    # And the following are crap
    faulty_ids.extend([338, 339])
    # 335 is a duplicate of 336
    faulty_ids.extend([335, ])
    combined_df = combined_df[~combined_df.image_id.isin(faulty_ids)]

    print combined_df[['DOI', 'url_collection', 'name_image', 'file']]

    #restrict to Z-, F-, or T-maps
    combined_df = combined_df[combined_df['map_type'].isin(["Z","F","T"])]
    terms_df = get_neurosynth_terms(combined_df)
    print combined_df["name_collection"].value_counts()
    combined_df = combined_df.merge(terms_df, on=['image_id', ])

    dest_dir = "/tmp/neurovault_analysis"
    target = "/usr/share/fsl/data/standard/MNI152_T1_2mm.nii.gz"

    combined_df = mem.cache(download_and_resample)(combined_df,
                                                   dest_dir, target)

    # Now remove -3360, -3362, and -3364, that are mean images, and not Z
    # scores
    not_Zscr = [-3360, -3362, -3364]
    combined_df = combined_df[~combined_df.image_id.isin(not_Zscr)]

    # Now remove images that are ugly, or obviously not z maps:
    broken = [1202, 1163, 1931, 1101, 1099]
    combined_df = combined_df[~combined_df.image_id.isin(broken)]

    combined_df.to_csv('%s/metadata.csv' % dest_dir, encoding='utf8')


    #--------------------------------------------------
    # Plot a map of frequency of activation
    freq_nii = get_frequency_map(combined_df, dest_dir, target)
    freq_nii.to_filename("freq_map.nii.gz")

    display = plot_anat("/usr/share/fsl/data/standard/MNI152_T1_2mm.nii.gz",
                        display_mode='z',
                        cut_coords=np.linspace(-30, 60, 7))
    display.add_overlay(freq_nii, vmin=0, cmap=plt.cm.hot,
                        colorbar=True)
    display._colorbar_ax.set_yticklabels(["% 3i" % float(t.get_text())
            for t in display._colorbar_ax.yaxis.get_ticklabels()])
    display.title('Percentage of activations (Z or T > 3)')

    display.savefig('activation_frequency.png')
    display.savefig('activation_frequency.pdf')


    #--------------------------------------------------
    # Plot the frequency of occurence of neurosynth terms
    # Use the terms from neurosynth to label the ICAs
    terms = combined_df[[c for c in combined_df.columns
                         if c.startswith('neurosynth decoding')]]
    terms = terms.fillna(0)
    term_matrix = terms.as_matrix()
    # Labels that have a negative correlation are not present in the map
    term_matrix[term_matrix < 0] = 0

    term_names = [c[20:] for c in combined_df.columns
                  if c.startswith('neurosynth decoding')]

    plt.figure(figsize=(5, 20))
    plt.barh(np.arange(len(term_names)), term_matrix.sum(axis=0))
    plt.axis('off')
    plt.axis('tight')
    plt.tight_layout()
    for idx, name in enumerate(term_names):
        plt.text(.1, idx + .1, name)
    plt.savefig('term_distribution.pdf')


    plt.show()
