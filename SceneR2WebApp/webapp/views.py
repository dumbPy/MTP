from django.http import HttpResponse
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
from .forms import UploadVideoAndCANForm
import os
import pkg_resources
from .process import process_can_and_video
from django.templatetags.static import static
from PIL import Image
import numpy as np, pickle

# def index(request):
#     return render(request, 'index.html')

def index(request):
    if request.method == 'POST':
        form = UploadVideoAndCANForm(request.POST, request.FILES)

        if form.is_valid():
            form = form.save()
            out_folder = os.path.join(settings.MEDIA_ROOT, 'processed')
            message, params = process_can_and_video(out_folder,
                        form.can.path, form.video.path, form.yolo)
            video_name = os.path.split(form.video.path)[-1]
            video_name = ".".join(video_name.split('.')[:-1]+['mp4'])
            form = UploadVideoAndCANForm()
            messages.info(request, message)
            context = {'form':form,
                    'video_path':f'/media/processed/{video_name}',
                    'can_slider_path': f'/media/processed/can_slider.png',
                    'can_image_full': f'/media/processed/can_image_full.png',
                    'can_few_cols': f'/media/processed/can_few_cols.png'}
            context.update(params)
            return  render(request, 'output.html', context)
        else:
            form = UploadVideoAndCANForm()
            messages.error(request, 'Invalid Uploads extensions, video should be either mp4 or avi and CAN should be a csv files')
            return render(request, 'index.html', {'form':form})
    else:
        form = UploadVideoAndCANForm()
    default_folder = os.path.join(settings.MEDIA_ROOT, 'defaults')
    slider_size = Image.open(os.path.join(default_folder,  'can_slider_default.png')).size
    w,h = slider_size
    slider_height = 0.9*h
    messages.info(request, "Pedestrian Crossing Left to Right")
    with open(os.path.join(default_folder, 'dy_col_default_ped.pt'),'rb') as f:
        dy_col_default = pickle.load(f)
    # Returning default video and can just for the sake of demonstration.
    # Usually, it should return index.html instead.
    # return render(request, 'index.html', {'form':form})
    return render(request, 'output.html', {'form':form,
                    'video_path':'/media/defaults/video_default.mp4',
                    'can_slider_path': "/media/defaults/can_slider_default.png",
                    'len_can':996,
                    'slider_height': f'{slider_height}px',
                    'len_video':498,
                    'dy_col': dy_col_default})
