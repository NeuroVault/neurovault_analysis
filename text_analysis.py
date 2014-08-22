import os
import re

import pandas as pd
import numpy as np

def to_str(value):
    if isinstance(value, float):
        return ''
    else:
        value = str(value).replace('.nii', '').replace('.gz', '')
        value = value.lower()
        value = ' %s ' % value
        exp = re.compile(r"[-_.;,:!?'()]")
        value = exp.sub(' ', value)
        #for word in exclude_words:
        #    value = value.replace(' %s ' % word, ' ')
        return value

def extract_documents(metadata, collection_data=False):
    documents = []
    for _, row in metadata.iterrows():
        this_doc = [to_str(row.description_image),
                    to_str(row.name_image)]
        if collection_data:
            # Repeat the 3 time image-specific info, to give them more weight
            this_doc = 3 * this_doc
            this_doc.extend((to_str(row.description_collection),
                             to_str(row.name_collection)))

        this_doc = ' '.join(this_doc)
        # Replace spaces by 2 consecutive spaces, to make life easier for
        # the matching code that follows
        this_doc = ' %s ' % re.sub(r'\s+', '  ', this_doc)
        documents.append(this_doc)
    return documents


# Groups of terms that appear often (careful to only have double spaces)
groups = [
          ('semantic', 'linguistic', 'language', 'word', 'words',
          'reading', 'verb', 'voice'),
          ('motor', 'button', 'hand'),
          ('face', 'imagery', 'scrambled', 'checkerboard'),
         ]

group_names = ('language', 'audio', 'motor', 'visual', )

def vectorize(documents):
    # A hand-code vectorizer (probably horrible):
    X = []
    for this_doc in documents:
        this_x = list()
        for this_group in groups:
            this_count = 0
            for word in this_group:
                this_count += len(re.compile(' %s ' % word).findall(this_doc))
            this_x.append(this_count)
        X.append(this_x)

    X = np.array(X)
    return X


if __name__ == '__main__':
    from matplotlib import pyplot as plt

    data_dir = "/tmp/neurovault_analysis"

    metadata = pd.DataFrame.from_csv(os.path.join(data_dir, 'metadata.csv'))

    documents = extract_documents(metadata)
    X = vectorize(documents)

    plt.imshow(X, aspect='auto', interpolation='nearest')
    plt.xticks(range(len(group_names)), group_names)
    plt.show()
