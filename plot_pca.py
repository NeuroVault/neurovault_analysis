import os

import numpy as np
import pandas as pd
import seaborn as sns
sns.set_style("whitegrid")

from matplotlib import pyplot as plt
from nilearn.input_data import NiftiMasker
from sklearn.preprocessing import LabelEncoder

# -------------------------------------------
# loading data and metadata

data_dir = "/tmp/neurovault_analysis"
mask = 'gm_mask.nii.gz'

metadata = pd.DataFrame.from_csv(os.path.join(data_dir, 'metadata.csv'))

# replace NaNs by unknown
metadata.fillna('unknown')

# can choose another target field here
target = metadata['collection_id'].values
le = LabelEncoder()
y = le.fit_transform(target)

images = [os.path.join(data_dir, 'resampled',
                       '%06d.nii.gz' % row[1]['image_id'])
          for row in metadata.iterrows()]

masker = NiftiMasker(mask_img=mask, memory=os.path.join(data_dir, 'cache'))
X = masker.fit_transform(images)

from text_analysis import GROUP_NAMES, extract_documents, vectorize

documents = extract_documents(metadata)
term_freq = vectorize(documents)

# -------------------------------------------
# ugly code to plot scatter matrices

import matplotlib.colors
#from scipy.stats import gaussian_kde


def factor_scatter_matrix(df, factor, factor_labels, legend_title=None,
                          palette=None, title=None):
    '''Create a scatter matrix of the variables in df, with differently colored
    points depending on the value of df[factor].
    inputs:
        df: pandas.DataFrame containing the columns to be plotted, as well
            as factor.
        factor: string or pandas.Series. The column indicating which group
            each row belongs to.
        palette: A list of hex codes, at least as long as the number of groups.
            If omitted, a predefined palette will be used, but it only includes
            9 groups.
    '''

    if isinstance(factor, basestring):
        factor_name = factor  # save off the name
        factor = df[factor]  # extract column
        df = df.drop(factor_name, axis=1)  # remove from df, so it
        # doesn't get a row and col in the plot.

    classes = list(set(factor))

    if palette is None:
        palette = sns.color_palette("gist_ncar", len(set(factor)))
    elif isinstance(palette, basestring):
        palette = sns.color_palette(palette, len((set(factor))))
    else:
        palette = sns.color_palette(palette)

    color_map = dict(zip(classes, palette))

    if len(classes) > len(palette):
        raise ValueError((
            "Too many groups for the number of colors provided."
            "We only have {} colors in the palette, but you have {}"
            "groups.").format(len(palette), len(classes)))

    colors = factor.apply(lambda group: color_map[group])
    axarr = scatter_matrix(df, figsize=(10, 10),
                           marker='o', c=np.array(list(colors)), diagonal=None,
                           alpha=1.0)

    if legend_title is not None:
        plt.grid('off')
        plt.legend([plt.Circle((0, 0), fc=color) for color in palette],
                factor_labels, title=legend_title, loc='best',
                ncol=3)
    if title is not None:
        plt.suptitle(title)

    # for rc in xrange(len(df.columns)):
    #     for group in classes:
    #         y = df[factor == group].icol(rc).values
    #         gkde = gaussian_kde(y)
    #         ind = np.linspace(y.min(), y.max(), 1000)
    #         axarr[rc][rc].plot(ind, gkde.evaluate(ind), c=color_map[group])

    return axarr, color_map

# -------------------------------------------
# quick PCA and plotting

from sklearn.decomposition import PCA
from pandas.tools.plotting import scatter_matrix

pca = PCA(n_components=3)
X_pca = pca.fit_transform(X)

df_pca = pd.DataFrame(dict(zip(np.arange(pca.n_components), X_pca.T)))

scatter_matrix(df_pca, alpha=0.2, figsize=(6, 6), diagonal='kde')


df_pca['label'] = y
factor_scatter_matrix(df_pca, 'label', le.inverse_transform(list(set(y))),
                      'collection_id')

if 0:
    # -------------------------------------------
    # T-SNE

    from sklearn.manifold import TSNE

    tsne = TSNE(n_components=3, perplexity=5)
    X_tsne = tsne.fit_transform(X.astype('float64'))

    df_tsne = pd.DataFrame(dict(zip(np.arange(tsne.n_components), X_tsne.T)))
    df_tsne['label'] = y
    factor_scatter_matrix(df_tsne, 'label', le.inverse_transform(list(set(y))),
                        'collection_id')

if 0:
    # -------------------------------------------
    # MSD

    from sklearn.manifold import MDS

    mds = MDS(n_components=3)
    X_mds = mds.fit_transform(X.astype('float64'))

    df_mds = pd.DataFrame(dict(zip(np.arange(mds.n_components), X_mds.T)))
    df_mds['label'] = y
    factor_scatter_matrix(df_mds, 'label', le.inverse_transform(list(set(y))),
                        'collection_id')


    for freq, name in zip(term_freq.T, GROUP_NAMES):
        df_mds['label'] = freq
        factor_scatter_matrix(df_mds, 'label',
                            le.inverse_transform(list(set(y))),
                            title=name, palette='hot')


plt.show()
