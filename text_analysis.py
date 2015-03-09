""" Text analysis on the metadata, to infer some topics and terms
"""
# Author: Gael Varoquaux
# License: BSD

import re

import numpy as np


# Groups of terms that appear often (careful to only have double spaces)
GROUPS = [
          ('semantic', 'linguistic', 'language', 'word', 'words',
           'reading', 'verb', 'voice'),
          ('audio', 'auditory', 'audition', 'listening', 'tone'),
          ('motor', 'button', 'hand', 'finger', 'foot'),
          ('button', 'hand', 'finger'),
          ('imagery', 'color', 'photo',
           'visual', 'visually', 'viewing', 'pictures',
           #'house',
          ),
          (
           'checkerboard', 'scrambled',
          ),
          ('shoe', 'chair', 'bottle', 'scissors', 'house', 'cat'),
         ]

GROUP_NAMES = ('language', 'audio', 'motor', 'hand', 'visual terms',
               'secondary visual',
               'objects')


def to_str(value):
    if isinstance(value, float):
        return ''
    else:
        value = str(value).replace('.nii', '').replace('.gz', '')
        value = value.lower()
        value = ' %s ' % value
        exp = re.compile(r"[_.;,:!?'()]")
        value = exp.sub(' ', value)
        #for word in exclude_words:
        #    value = value.replace(' %s ' % word, ' ')
        return value


def extract_documents(metadata, collection_data=False):
    documents = []
    def my_to_str(x):
        return re.sub('(-|>|vs).*$', ' ', to_str(x))
    for _, row in metadata.iterrows():
        this_doc = [my_to_str(row.description_image),
                    my_to_str(row.name_image),
                    my_to_str(row.contrast_definition),
                    my_to_str(row.contrast_definition_cogatlas)]
        if collection_data:
            # Repeat the 3 time image-specific info, to give them more weight
            this_doc = 3 * this_doc
            this_doc.extend((to_str(row.description_collection),
                             to_str(row.name_collection)))

        this_doc = ' '.join(this_doc)
        # Replace '>' by ' '
        # Replace spaces by 2 consecutive spaces, to make life easier for
        # the matching code that follows
        this_doc = ' %s ' % re.sub(r'\s+', '  ', this_doc)
        documents.append(this_doc)
    return documents


def vectorize(documents):
    # A hand-code vectorizer (probably horrible):
    X = []
    for this_doc in documents:
        this_x = list()
        for this_group in GROUPS:
            this_count = 0
            for word in this_group:
                this_count += len(re.compile(' %s ' % word).findall(this_doc))
            this_x.append(this_count)
        X.append(this_x)

    X = np.array(X)
    return X


