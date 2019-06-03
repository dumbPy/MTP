from torch.utils.data import Dataset as BaseDataset
from .core import *


class oneVidNumpyDataset(BaseDataset):
    def __init__(self, fileName:str,resolution:tuple=(224,224), skipStart=125, skipEnd=125, get_label=None)->BaseDataset:
        """Dataset for extracting frames from passed .npy file and corrosponding labels from get_label
        """
        self.fileName=fileName
        self.get_label=get_label
        self.skipStart=skipStart
        self.skipEnd=skipEnd
        self.res=resolution
    
    def __getitem__(self,idx:int)->tuple:
        #skipping the first and last 125 frames.
        idx+=self.skipStart
        x=np.load(self.fileName)[idx]
        x=np.squeeze(x)     #extra 1 dimention removed if any
        if len(x.shape)==2 : x=np.dstack((x,x,x)) #id image is 1 channel, make it 3 channel
        x=np.rollaxis(x, 2)   #Make the images channel first
        x=x[:,:224,:224].astype("float32")
        return (x, self.get_label(self.fileName, idx))
    
    def get_y(self, idx):
        return self.get_label(self.fileName, idx+self.skipStart)
    
    def __len__(self):
        return len(np.load(self.fileName))-self.skipStart-self.skipEnd


class ConcatDatasetWithWeights(torch.utils.data.ConcatDataset):
    def __init__(self, fileNames, get_label):
        self.fileNames=fileNames
        self.get_label=get_label
        datasets=[oneVidNumpyDataset(fileName, get_label=get_label) for fileName in fileNames]
        super().__init__(datasets)
    
    @staticmethod
    def fixLabelLength(labels, dataset):
        """If labels of some trailing frames are missing, broadcast last label to all trailing frames
        If labels are more than frames, remove the extra labels from end"""
        labels=list(labels)
        while len(labels)<len(dataset):
            labels+=labels[-1]
        while len(labels)>len(dataset):
            labels.pop() #remove last extra element
        return labels
    
    def get_y(self, idx):
        import bisect
        dataset_idx = bisect.bisect_right(self.cumulative_sizes, idx)
        if dataset_idx == 0:
            sample_idx = idx
        else:
            sample_idx = idx - self.cumulative_sizes[dataset_idx - 1]
        return self.datasets[dataset_idx].get_y(sample_idx)
    
    def getWeights(self):
        try: _=self.weights
        except:
            allLabels=[self.get_y(i) for i in range(self.__len__())]
            classes=set(allLabels)                     #will return all classes
            counts = [allLabels.count(someClass) for someClass in classes]
            self.weights=[1/counts[label] for label in allLabels] #convert labels to weights as weight=1/count[label]
        return self.weights 

class dumbWeightedRandomSampler(torch.utils.data.Sampler):
    """weightedRandomSampler like torch.utils.data.weightedRandomSampler but with numpy insices rather than torch"""
    def __init__(self, weights, num_samples, replacement=True):
        from torch._six import int_classes as _int_classes
        if not isinstance(num_samples, _int_classes) or isinstance(num_samples, bool) or \
                num_samples <= 0:
            raise ValueError("num_samples should be a positive integeral "
                             "value, but got num_samples={}".format(num_samples))
        if not isinstance(replacement, bool):
            raise ValueError("replacement should be a boolean value, but got "
                             "replacement={}".format(replacement))
        self.weights = weights
        self.num_samples = num_samples
        self.replacement = replacement        
        
    def __iter__(self):
        import random
        return iter(random.choices(list(range(len(self.weights))), weights=self.weights, k=self.num_samples))

    def __len__(self):
        return self.num_samples


def vid_from_csv(file_id, vid_folder=None, vid_format='mp4'):
    """
    Returns: path_to_video if exists or raises a NameError
    """
    if vid_folder is None: 
        assert(os.path.exists(globalVariables.path_to_vids)),\
                "please update globalVariables.path_to_vids or pass vid_folder as argument. default path does not exists"
        vid_folder=globalVariables.path_to_vids
    vid_files=glob(os.path.join(vid_folder, '*'+vid_format))
    assert(len(vid_files)>0), "No Video Files Found in "+vid_folder+" \
        make sure the location is mounted"
    for vidFile in vid_files:
        if file_id in  vidFile: return vidFile
    raise NameError(file_id+" not found in "+vid_folder)


class StandardSequenceScaler(StandardScaler):
    """
    StandardScaler for sequencial data.
    see https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html
    for documentation on StandardScaler
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def fit(self, X):
        """
        X : {array-like, sparse matrix} of shape [n_samples, n_sequence, n_features], 
            or list of length 'n_samples' of 2D array-like X's each of shape [n_sequence, n_features]
            
            Pass X as list of sequences when all sequences are not of same shape

            The data used to compute the mean and standard deviation
            used for later scaling along the features axis.
        """
        X=[xi[j] for xi in X for j in range(len(xi))]
        return super().fit(X)

    def transform(self, X, copy=None):
        """
        X:  {array-like or sparse matrix} of shape [n_sequence, n_features]
            or [n_samples, n_sequence, n_features]
            or list of Xs each of shape [n_sequence, n_features] 
            with each Xs having independent n_sequence
        
        Returns:
            transformed_X of the same type i.e., list or array as given
        """
        copy = copy if copy is not None else self.copy
        #X as list of Xs each of shape [n_sequence, n_features]
        if isinstance(X, list):
            """multiple x to transform
            As all sequences might not be of 
            the same size, we cannot stack them into array"""
            return [super().transform(Xi, copy=copy) for Xi in X]
        #X as an array of shape [n_samples, n_sequence, n_features]
        if isinstance(X, np.ndarray):
            if len(X.shape)==3:
                oldshape=X.shape
                newshape=[X.shape[0]*X.shape[1], X.shape[2]]
                X=X.reshape(X, newshape)
                X=super().transform(X, copy=copy)
                return np.reshape(X, oldshape)
        #single X
        return super().transform(X, copy=copy)

    def inverse_transform(self, X, copy=None):
        copy = copy if copy is not None else self.copy
        #X as list of Xs each of shape [n_sequence, n_features]
        if isinstance(X, list):
            """multiple x to inverse transform
            As all sequences might not be of 
            the same size, we cannot stack them into array"""
            return [super().inverse_transform(Xi, copy=copy) for Xi in X]
        #X as an array of shape [n_samples, n_sequence, n_features]
        if isinstance(X, np.ndarray):
            if len(X.shape)==3:
                oldshape=X.shape
                newshape=[X.shape[0]*X.shape[1], X.shape[2]]
                X=X.reshape(X, newshape)
                X=super().inverse_transform(X, copy=copy)
                return np.reshape(X, oldshape)
        #single X
        return super().inverse_transform(X, copy=copy)

class VidLoader:
    """Video Loader for loading videos to be loaded and sliced on the fly
    imageio.get_reader is a good video loader but it requires slicing index
    to be saved in seperate variable. This class encapsulate that
    """
    def __init__(self,path, end:int, start=0, size:tuple=None):
        self.path = path
        self.end = end
        self.start = start
        self.size=size
    
    def resize(self, vid):
        if self.size is None: return vid
        

    def __iter__(self):
        return iter(self.data)
    @property
    def data(self):
        video = np.stack([f for i,f in enumerate(imageio.get_reader(self.path))])
        vid = video[self.start:self.end].copy()
        del video
        vid = np.moveaxis(vid, 3,1)
        return vid
        
    def __len__(self):
        return len(imageio.get_reader(self.path))

def get_frames(path, end:int=np.infty, start:int=0, shape:tuple=None):
    from skimage.transform import resize
    for i,frame in enumerate(imageio.get_reader(path)):
        if i >= start and i <= end:
            if shape is not None: frame = resize(frame, shape)
            frame = np.moveaxis(frame, 2, 0)
            yield frame


def makeEven(n:int):
    if n%2==0: return n
    else: return n-1

# pad_tensor and PadCollate copied from 
# https://discuss.pytorch.org/t/dataloader-for-various-length-of-data/6418/8
def pad_tensor(vec, pad, dim):
    """
    args:
        vec - tensor to pad
        pad - the size to pad to
        dim - dimension to pad

    return:
        a new tensor padded to 'pad' in dimension 'dim'
    """
    pad_size = list(vec.shape)
    # print(vec.shape[dim])
    pad_size[dim] = pad - vec.shape[dim]
    if isinstance(vec, np.ndarray): vec=torch.from_numpy(vec).float()
    return torch.cat([vec, torch.zeros(*pad_size)], dim=dim)


class PadCollate:
    """
    a variant of callate_fn that pads according to the longest sequence in
    a batch of sequences
    Returns
    -------
    xs:         concatinated, padded x tensors
    ys:         concatinated, padded y tensors
    x_sizes:    original size of x tensors
    """

    def __init__(self, dim=0):
        """
        args:
            dim - the dimension to be padded (dimension of time in sequences)
        """
        self.dim = dim

    def pad_collate(self, batch):
        """
        args:
            batch - list of (tensor, label)

        reutrn:
            xs - a tensor of all examples in 'batch' after padding
            ys - a LongTensor of all labels in batch
        """
        
        # find longest sequence
        x_sizes = [x.shape[0] for x,y in batch]
        max_len = max(x_sizes)
        # pad according to max_len
        batch = [(pad_tensor(x, pad=max_len, dim=self.dim), y) 
                    for x,y in batch]
        # stack all
        xs = torch.stack([x for x,y in batch], dim=0)
        ys = torch.LongTensor([y for x,y in batch])
        return xs, ys, x_sizes

    def __call__(self, batch):
        return self.pad_collate(batch)

def fig2rgb_array(fig):
    """
    Get the matplotlib figure's buffer as a numpy array
    Can be used to get drawn figures and images as numpy 
    array without saving
    """
    fig.canvas.draw()
    buf = fig.canvas.tostring_rgb()
    ncols, nrows = fig.canvas.get_width_height()
    return np.fromstring(buf, dtype=np.uint8).reshape(nrows, ncols, 3)