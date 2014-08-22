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

ica_img = masker.inverse_transform(ica_maps)
ica_img.to_filename('ica.nii.gz')

# Use the terms from neurosynth to label the ICAs
terms = metadata[[c for c in metadata.columns
                  if c.startswith('neurosynth decoding')]]
terms = terms.fillna(0)
term_matrix = terms.as_matrix()
# Keep only the 10 first values per entry, as Neurosynth is not reliable
# in the tails
#for col in term_matrix:
#    col[col < np.sort(col)[-10]] = 0
term_matrix[term_matrix < .33] = 0

# Not using the transform method as it shifts by the mean learned on
# data
ica_terms = np.dot(term_matrix.T, fast_ica.components_.T).T
col_names = [c[20:] for c in metadata.columns
             if c.startswith('neurosynth decoding')]

try:
    # Generate figures

    # word_cloud install via
    # pip install --user git+https://github.com/amueller/word_cloud.git
    from pytagcloud import create_tag_image, make_tags
    from scipy import stats
    from nilearn.plotting import plot_stat_map

    def scalef(count, mincount, maxcount, minsize, maxsize):
        count = float(count - mincount) / (maxcount - mincount)
        count *= .99 * maxsize
        return int(count)

    for idx, (ic, ic_terms) in enumerate(zip(ica_maps, ica_terms)):
        count_thr = stats.scoreatpercentile(np.abs(ic_terms), 75)
        this_count = [(w, np.abs(c)) for w, c in zip(col_names, ic_terms)
                      if np.abs(c) > count_thr]
        colors = [((255, 0, 0) if c > 0 else (0, 0, 255)) for c in ic_terms
                      if np.abs(c) > count_thr]

        tags = make_tags(this_count, maxsize=120, scalef=scalef,
                         colors=colors)

        create_tag_image(tags,
                         'component_%i_terms.png' % idx, size=(900, 600),
                         #fontname='Molengo', layout=3)
                         fontname='Lobster', layout=3)
        ic_thr = stats.scoreatpercentile(np.abs(ic), 85)
        ic_img = masker.inverse_transform(ic)
        plot_stat_map(ic_img, threshold=ic_thr)
        plt.savefig('component_%i_ic.png' % idx)
except ImportError:
    pass


plt.show()
