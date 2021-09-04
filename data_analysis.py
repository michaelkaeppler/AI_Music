from argparse import ArgumentParser
from pretty_midi import PrettyMIDI
import pypianoroll
import numpy as np
import pandas as pd
import glob
import os
from tqdm import tqdm
import json

class MidiClass:
    def __init__(self, path):
        # read
        mt = pypianoroll.read(path)
        
        # basic stats
        #try:
        self.resolution = int(mt.resolution)
        #except:
        #    self.resolution = -1
        #if len(np.unique(mt.tempo)) > 1:
        #    raise RuntimeError
        #else:
        #try:
        self.tempo = [int(i) for i in np.unique(mt.tempo)]#[0]
        self.sum_tempo = int(np.sum(mt.tempo))
        #except:
        #    self.tempo = -1
        
        # tracks stats
        tracks = mt.tracks
        self.n_tracks = len(tracks)
        self.programs = []
        self.uses_drum = False
        
        notes = np.zeros(tracks[0].pianoroll.shape, dtype=bool)
        self.len = notes.shape[0]
        for track in tracks:
            self.programs.append(track.program)
            if track.is_drum:
                self.uses_drum = True
            else:
                notes += track.pianoroll > 0
        
        notes_per_frame = notes.sum(1)
        self.silent_start = int(sum(np.cumsum(notes_per_frame) == 0))
        self.silent_end = int(sum(np.cumsum(notes_per_frame[::-1]) == 0))
        
        self.silent_middle = int(sum(notes_per_frame[self.silent_start:-self.silent_end] == 0))
        self.notes_in_bin = [int(i) for i in notes.sum(0)]#/notes.sum()

def get_last_file_number(path):
    file_names = glob.glob(os.path.join(path, '*.json'))
    if file_names:
        last_file = file_names[-1]
        number_with_extension = last_file.split('_')[-1]
        number = number_with_extension.split('.')[0]
        return int(number)
    else:
        return 0

current_file_number = 0

def log_data(path, song_dict):
    global current_file_number
    with open(os.path.join(path, 'song_'+str(current_file_number).zfill(6)+'.json'), 'w') as f:
        json.dump(song_dict, f)
    current_file_number += 1

if __name__ == '__main__':
    parser = ArgumentParser()
    # model args
    parser.add_argument('--midi_path', type = str, default = "midis_cpdl/", help='N')
    parser.add_argument('--data_path', type = str, default = "song_data_cpdl/", help='N')#ethicscommonsense

    args = parser.parse_args()

    file_names = glob.glob(os.path.join(args.midi_path, '**/*.mid*'), recursive=True)
    #print(len(file_names))
    #print(1/0)
    current_file_number = get_last_file_number(args.data_path) + 1
    for file_name in tqdm(file_names):
        try:
            song = MidiClass(file_name)
            name = os.path.split(file_name)[-1]
            log_data(args.data_path, {name:song.__dict__})
        except:
            pass