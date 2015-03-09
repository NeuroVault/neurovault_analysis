import os

import pandas as pd

from scipy import stats
from matplotlib import pyplot as plt

from nilearn.input_data import NiftiMasker
from nilearn.plotting import plot_stat_map

from text_analysis import GROUP_NAMES, extract_documents, vectorize


# -------------------------------------------
# loading data and metadata

data_dir = "/tmp/neurovault_analysis"
mask = 'gm_mask.nii.gz'

metadata = pd.DataFrame.from_csv(os.path.join(data_dir, 'metadata.csv'))

images = [os.path.join(data_dir, 'resampled',
                       '%06d.nii.gz' % row[1]['image_id'])
          for row in metadata.iterrows()]

masker = NiftiMasker(mask_img=mask, memory=os.path.join(data_dir, 'cache'))
X = masker.fit_transform(images)

documents = extract_documents(metadata)
term_freq = vectorize(documents)

all_img = masker.inverse_transform(X.mean(axis=0))
all_img.to_filename('all.nii.gz')
display = plot_stat_map(all_img, cut_coords=(-14, 8, 26, 44, 54),
                        colorbar=False,
                        display_mode='z')
display.title('all: %i maps' % len(X), size=17)
display.savefig('all.png')
display.savefig('all.pdf')

for name, term_vector in zip(GROUP_NAMES, term_freq.T):
    # The mean image
    term_img = masker.inverse_transform(X[term_vector != 0].mean(axis=0))
    term_img.to_filename('%s.nii.gz' % name)

    display = plot_stat_map(term_img, cut_coords=(-14, 8, 26, 44, 54),
                            colorbar=False, display_mode='z')
    display.title('%s: %i maps' % (name, (term_vector != 0).sum()),
                  size=17)
    display.savefig('%s.png' % name)
    display.savefig('%s.pdf' % name)

    # The fraction of activated voxels, in ratio of how often the
    # corresponding voxels are activated in the full database
    diff = stats.ttest_ind(X[term_vector != 0],
                           X[term_vector == 0])[0]
    term_img = masker.inverse_transform(diff)
    term_img.to_filename('%s_relative.nii.gz' % name)

    # The threshold of T = 5 corresponds to an FWER correction on a 3x3x3
    # gm grid.
    display = plot_stat_map(term_img, cut_coords=(-14, 8, 26, 44, 54),
                            #colorbar=False,
                            threshold=5.,
                            display_mode='z',
                            vmax=12.)
    display.title('%s: %i maps' % (name, (term_vector != 0).sum()),
                  size=17)
    display.savefig('%s_t_stat.png' % name)
    display.savefig('%s_t_stat.pdf' % name)

plt.show()
