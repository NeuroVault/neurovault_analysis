"""
Perform an ICA analysis on the NeuroVault data, and label the ICA
maps using the labels inferred from the NeuroVault decoding.
"""
# Author: Gael Varoquaux
# License: BSD

import os

import numpy as np
import pandas as pd
from scipy import stats

from matplotlib import pyplot as plt
from sklearn.decomposition import FastICA

from nilearn.input_data import NiftiMasker
from nilearn.plotting import plot_stat_map

# -------------------------------------------
# load data and metadata
data_dir = "/tmp/neurovault_analysis"
mask = 'gm_mask.nii.gz'

metadata = pd.DataFrame.from_csv(os.path.join(data_dir, 'metadata.csv'))

images = [os.path.join(data_dir, 'resampled',
                       '%06d.nii.gz' % row[1]['image_id'])
          for row in metadata.iterrows()]

masker = NiftiMasker(mask=mask, memory=os.path.join(data_dir, 'cache'))
X = masker.fit_transform(images)

fast_ica = FastICA(n_components=20, random_state=42)
ica_maps = fast_ica.fit_transform(X.T).T

ica_img = masker.inverse_transform(ica_maps)
ica_img.to_filename('ica.nii.gz')

# Use the terms from neurosynth to label the ICAs
terms = metadata[[c for c in metadata.columns
                  if c.startswith('neurosynth decoding')]]
terms = terms.fillna(0)
term_matrix = terms.as_matrix()
# Labels that have a negative correlation are not present in the map
term_matrix[term_matrix < 0] = 0

# Don't use the transform method as it centers the data
ica_terms = np.dot(term_matrix.T, fast_ica.components_.T).T
col_names = [c[20:] for c in metadata.columns
             if c.startswith('neurosynth decoding')]

if not os.path.exists('ica_maps'):
    os.mkdir('ica_maps')

# -------------------------------------------
# Generate figures
for idx, (ic, ic_terms) in enumerate(zip(ica_maps, ica_terms)):
    if -ic.min() > ic.max():
        # Flip the map's sign for prettiness
        ic = -ic
        ic_terms = -ic_terms

    ic_thr = stats.scoreatpercentile(np.abs(ic), 90)
    ic_img = masker.inverse_transform(ic)
    # Use the 4 terms weighted most as a title
    important_terms = np.array(col_names)[np.argsort(ic_terms)[-4:]]
    display = plot_stat_map(ic_img, threshold=ic_thr, colorbar=False)
    display.title(', '.join(important_terms[::-1]), size=16)
    plt.savefig('ica_maps/component_%i_ic.png' % idx)
    plt.savefig('ica_maps/component_%i_ic.pdf' % idx)


