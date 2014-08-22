import os

import numpy as np
import pandas as pd

from matplotlib import pyplot as plt
from nilearn.input_data import NiftiMasker
from sklearn.decomposition import FastICA

# -------------------------------------------
# loading data and metadata

data_dir = "/tmp/neurovault_analysis"
mask = 'gm_mask.nii.gz'

metadata = pd.DataFrame.from_csv(os.path.join(data_dir, 'metadata.csv'))

images = [os.path.join(data_dir, 'resampled',
                       '%06d.nii.gz' % row[1]['image_id'])
          for row in metadata.iterrows()]

masker = NiftiMasker(mask=mask, memory=os.path.join(data_dir, 'cache'))
X = masker.fit_transform(images)

fast_ica = FastICA(n_components=20)
ica_maps = fast_ica.fit_transform(X.T).T

from text_analysis import group_names, extract_documents, vectorize

documents = extract_documents(metadata)
term_freq = vectorize(documents)

ica_img = masker.inverse_transform(ica_maps)
ica_img.to_filename('ica.nii.gz')

plt.show()
