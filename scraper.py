# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 22:18:28 2014

@author: sunshine
"""

import pandas as pd
import os
import os.path as osp
import sys
import requests as rq
import subprocess


#sorts the rows by the loop count, drop duplicates, and resets the index
def sort_clean(data):
    data_sorted = data.sort(columns=['count'], ascending=False)
    data_cleaned = data_sorted.drop_duplicates(subset='permalinkUrl')
    data_reindex = data_cleaned.reset_index(drop=True)
    return data_reindex


#gets the absolute path of the directory and append the path to it
def abs_path(path):
    return osp.join(osp.dirname(osp.abspath(sys.argv[0])), path)


#checks all the id's of the vines to see if there is a corresponding file
#in the specified directory, if wrong directory method returns empty DataFrame
def vine_exists(data, directory):
    if directory in ['cache', 'render']:
        #filter lambda for the dataframe
        is_file = lambda vineid: osp.isfile(abs_path(directory + '/' + str(vineid) + '.mp4'))
        datav = data[data['id'].map(is_file)]
        return datav
    else:
        return pd.DataFrame()


def delete_file(path):
    path = abs_path(path)
    try:
        if osp.isfile(path):
            os.unlink(path)
    except Exception, e:
        print e


#gets rid of all files in the render and cache directories as well as
#the vine records csv and leftover temp mp3 audio clips
def flush_all():
    for directory in ['render/', 'render/groups/', 'cache/']:
        for vfile in os.listdir(abs_path(directory)):
            delete_file(directory + vfile)
    for vfile in os.listdir(abs_path('')):
        if vfile.endswith('.mp3'):
            print('removing: ' + vfile)
            delete_file(vfile)
    delete_file('records.csv')


def get_top_pages(pages):
    #composite dataframe to hold all the compiled information
    comp = pd.DataFrame()
    for page in range(0, pages + 1):
        url = 'https://api.vineapp.com/timelines/popular?page=%d' % page
        #vine object is the json object returned from the vine api
        try:
            vines = rq.get(url).json()
            #the meat of the json object we're looking for, vine entries
            df = pd.DataFrame.from_dict(vines['data']['records'])
            #if this is the first page, start comp as a copy of the page
            if page == 1:
                comp = df.copy()
            #else add current page to the comp
            else:
                comp = pd.concat([df, comp], ignore_index=True)
        except Exception as e:
            print(e)
    #expands the loops column's objects into count and velocity columns
    loops = comp['loops'].apply(lambda x: pd.Series(x))
    unstacked = loops.unstack().unstack().T[['count', 'velocity']]
    #adds the new columns to the previous page composite
    comp[['count', 'velocity']] = unstacked
    #takes the columns we need
    subset = comp[['count', 'velocity', 'videoUrl',
                   'permalinkUrl', 'description', 'username']].copy()
    get_id = lambda x: x.rsplit('/', 1)[-1]
    subset['id'] = [get_id(perma) for perma in subset['permalinkUrl']]
    sort = sort_clean(subset)
    return sort


def download_vines(data):
    #zip the data we need so we can run through with one loop
    zipped = zip(data['videoUrl'], data['id'], data['description'])
    for url, perma, desc in zipped:
        name = perma
        filename = abs_path('cache/' + name + '.mp4')
        # Download the file if it does not exist
        if not osp.isfile(filename):
            print('downloading ' + perma + ': ' + desc)
            with open(filename, 'wb') as fd:
                for chunk in rq.get(url, stream=True).iter_content(5000):
                    fd.write(chunk)


def update_records(data):
    #gets real path of file
    filename = abs_path('records.csv')
    #if the file exsts, combine file with new data
    if osp.isfile(filename):
        records = pd.read_csv(filename, encoding='utf-8')
        comp = sort_clean(pd.concat([data, records], ignore_index=True))
        comp.to_csv(filename, index=False, encoding='utf-8')
    #f file doesn't exist, save it for the first time
    else:
        data.to_csv(filename, index=False, encoding='utf-8')


def upload_video(path):
    if osp.isfile(path):
        args = (['python2', abs_path('youtube_upload.py'),
                '--email=vinecompauthority@gmail.com', 
                '--password=XXXXX',
                '--title="Hottest Vines of The Week 0000"', 
                '--category=Comedy',
                path])
        subprocess.call(args)
    else:
        print('File not found: ' + path)


if __name__ == "__main__":
    data = get_top_pages(4)
    if not data.empty:
        if len(sys.argv) > 1:
            if '-flush' in sys.argv:
                flush_all()
            if '-update' in sys.argv:
                update_records(data)
            if '-download' in sys.argv:
                download_vines(data)
            if '-upload' in sys.argv:
                upload_video(abs_path('render/groups/FINAL RENDER.mp4'))
        else:
            update_records(data)
