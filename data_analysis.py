from argparse import ArgumentParser
import pypianoroll
import numpy as np
import glob
import os
from tqdm import tqdm
import json
import multiprocessing
from functools import partial

class MidiClass:
    def __init__(self, mt):
        # basic stats
        self.resolution = int(mt.resolution)
        self.tempo = [int(i) for i in np.unique(mt.tempo)]#[0]

        # tracks stats
        tracks = mt.tracks
        self.n_tracks = len(tracks)
        self.programs = []
        self.uses_drum = False
        
        notes = np.zeros(tracks[0].pianoroll.shape, dtype=bool)
        self.len = notes.shape[0]

        # Which fraction of a beat does a timestep amount to?
        beat_fraction = 1 / self.resolution
        # How long does a beat last, for every timestep (there may be tempo changes
        # in the middle of the piece)
        beat_duration_seconds = 60 / mt.tempo
        # Total duration in seconds
        self.total_duration = int(np.sum(beat_duration_seconds * beat_fraction))


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


def process_file(input_path, output_path):
    try:
        mt = pypianoroll.read(input_path)
    except:
        return

    song = MidiClass(mt)
    name = os.path.split(input_path)[-1]
    song_dict = {name: song.__dict__}

    try:
        files = os.listdir(output_path)
        numbers = []
        for file in files:
            if file[-4:] == 'json':
                numbers.append(int(file.split('_')[-1].split('.')[0]))
        new_num = max(numbers)+1
    except:
        new_num = 0
        
    with open(os.path.join(output_path, 'song_'+str(new_num).zfill(6)+'.json'), 'w') as f:
        json.dump(song_dict, f)

if __name__ == '__main__':
    parser = ArgumentParser()
    JOBS = multiprocessing.cpu_count() - 1
    # model args
    parser.add_argument('--midi_path', type = str, default = "midis_cpdl/", help='N')
    parser.add_argument('--data_path', type = str, default = "song_data_cpdl/", help='N')#ethicscommonsense
    parser.add_argument('--jobs', type=int, default=JOBS, help='N')

    args = parser.parse_args()

    file_names = glob.glob(os.path.join(args.midi_path, '**/*.mid*'), recursive=True)
    file_count = len(file_names)

    print(f'Processing {file_count} files with {args.jobs} processes:')
    process_f = partial(process_file, output_path=args.data_path)
    with multiprocessing.Pool(processes=args.jobs) as p:
        for file in tqdm(p.imap_unordered(process_f, file_names), total=file_count):
            pass
