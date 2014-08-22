import os

import numpy as np
import pandas as pd

from matplotlib import pyplot as plt
from nilearn.input_data import NiftiMasker

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

from text_analysis import group_names, extract_documents, vectorize

documents = extract_documents(metadata)
term_freq = vectorize(documents)

all_img = masker.inverse_transform(X.mean(axis=0))
all_img.to_filename('all.nii.gz')

for name, term_vector in zip(group_names, term_freq.T):
    term_img = masker.inverse_transform(X[term_vector != 0].mean(axis=0))
    term_img.to_filename('%s.nii.gz' % name)

plt.show()
