"""
Compute a grey matter mask from the SPM Tissue Probability Masks
"""

import os
import numpy as np

from scipy import ndimage
from nilearn.image import resample_img
import nibabel

SPM_DIR = os.environ['SPM_DIR']

grey_matter_template = os.path.join(SPM_DIR, 'tpm', 'grey.nii')

brain_mask = nibabel.load(
  '/usr/share/fsl/data/standard/MNI152_T1_2mm_brain_mask.nii.gz'
  )

affine = brain_mask.get_affine()
shape = brain_mask.shape[:3]
brain_mask = brain_mask.get_data() > 1e-13

gm_img = nibabel.load(grey_matter_template)
gm_img =resample_img(gm_img, target_affine=affine, target_shape=shape)
gm_map = gm_img.get_data()
gm_mask = (gm_map > .33)

gm_mask = ndimage.binary_closing(gm_mask, iterations=2)
gm_mask = np.logical_and(gm_mask, brain_mask).astype(np.int)

mask_img = nibabel.Nifti1Image(gm_mask, affine)


nibabel.save(mask_img, 'gm_mask.nii.gz')

