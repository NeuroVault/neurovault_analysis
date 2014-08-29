""" Plot a map from neurosynth
"""
# Authors: Gael Varoquaux
# License: BSD

#import urllib, os, errno
#from urllib2 import Request, urlopen, HTTPError

import numpy as np
import pylab as plt

from nilearn.plotting.img_plotting import plot_anat

from neurosynth.base.dataset import Dataset
from neurosynth.analysis import meta


#def url_get(url):
#    request = Request(url)
#    response = urlopen(request)
#    return response.read()


if __name__ == '__main__':
    dataset = Dataset('/volatile/varoquau/dev/neurosynth-data/database.txt')
    ids = dataset.image_table.ids
    ma = meta.MetaAnalysis(dataset, ids)
    ma.save_results(prefix='all_neurosynth')

    #mem.clear()
    #combined_df = mem.cache(get_images_with_collections_df)()

    #--------------------------------------------------
    # Plot a map of frequency of activation

    display = plot_anat("/usr/share/fsl/data/standard/MNI152_T1_2mm.nii.gz",
                        display_mode='z',
                        cut_coords=np.linspace(-30, 60, 7))
    display.add_overlay('all_neurosynth_pA.nii.gz', vmin=0,
                        cmap=plt.cm.hot, colorbar=True)
    display._colorbar_ax.set_yticklabels([
            "% 3i" % (100 * float(t.get_text()))
            for t in display._colorbar_ax.yaxis.get_ticklabels()])
    display.title('NeuroSynth: Probability of activations')

    display.savefig('neurosynth_frequency.png')
    display.savefig('neurosynth_frequency.pdf')

    plt.show()
