from ..dataset import SingleCAN, TrackingObject, MovingObject, StationaryObject, PedestrianObject
from ..core import *
import cv2


class CanOverlayer:
    """Can Overlayer class
    Overlays the ith can signal from passed CAN data"""
    def __init__(self, dataset:SingleCAN):
        self.dataset = dataset
        # self.mult = multiplier
    
    def __call__(self, ax:plt.Axes, i):
        objs = self.dataset.allObjects
        objs = [obj for obj in objs if isinstance(obj, TrackingObject)]
        for obj in objs:
            color = self.get_color(obj)
            y = np.asarray(obj.y)
            det_col = np.asarray(obj.det_col)
            idx = i*2
            if det_col[idx] != 0:
                x_max = np.diff(ax.get_xlim())[0] # get x axis limits 
                ax.axvline(-y[idx] * x_max /8 + x_max/2, color=color)

    @staticmethod
    def get_color(object:TrackingObject):
        if isinstance(object, MovingObject): return 'red'
        elif isinstance(object, PedestrianObject): return 'green'
        elif isinstance(object, StationaryObject): return 'yellow'
        else: 
            raise TypeError('Passed object is not in TrackingObject subclasses')