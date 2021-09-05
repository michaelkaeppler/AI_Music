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
    def __init__(self, path):
        # read
        mt = pypianoroll.read(path)

        # tracks stats
        tracks = mt.tracks
        self.n_tracks = len(tracks)
        self.programs = []
        self.uses_drum = False
        
        notes = np.zeros(tracks[0].pianoroll.shape, dtype=bool)
        self.len = notes.shape[0]

        # Which fraction of a beat does a timestep amount to?
        beat_fraction = 1 / mt.resolution
        # How long does a beat last, for every timestep (there may be tempo changes
        # in the middle of the piece)
        beat_duration_seconds = 60 / mt.tempo
        # Total duration in seconds
        self.total_duration = int(np.sum(beat_duration_seconds * beat_fraction))
        # Average tempo in bpm
        beats_total = int(self.len * beat_fraction)
        self.tempo = int(beats_total / (self.total_duration / 60))

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

def get_first_new_file_number(path):
    file_names = glob.glob(os.path.join(path, '*.json'))
    if file_names:
        last_file = file_names[-1]
        number_with_extension = last_file.split('_')[-1]
        number = number_with_extension.split('.')[0]
        return int(number) + 1
    else:
        return 0

def init_file_counter(counter):
    global current_file_number
    current_file_number = counter

def process_file(input_path, output_path):
    try:
        song = MidiClass(input_path)
    except Exception as e:
        print(f'File {input_path} could not be processed: {str(e)}')
        return

    name = os.path.split(input_path)[-1]
    song_dict = {name: song.__dict__}

    global current_file_number

    with current_file_number.get_lock():
        with open(os.path.join(output_path, 'song_'+str(current_file_number.value).zfill(6)+'.json'), 'w') as f:
            json.dump(song_dict, f)

        current_file_number.value += 1

if __name__ == '__main__':
    parser = ArgumentParser()
    jobs = multiprocessing.cpu_count() - 1
    # model args
    parser.add_argument('--midi_path', type = str, default = "midis_cpdl/", help='N')
    parser.add_argument('--data_path', type = str, default = "song_data_cpdl/", help='N')#ethicscommonsense
    parser.add_argument('--jobs', type=int, default=jobs, help='N')

    args = parser.parse_args()

    file_names = glob.glob(os.path.join(args.midi_path, '**/*.mid*'), recursive=True)
    file_count = len(file_names)

    first_file_number = get_first_new_file_number(args.data_path)
    current_file_number = multiprocessing.Value('i', first_file_number)

    os.makedirs(args.data_path, exist_ok=True)
    if first_file_number > 0:
        print(f'Found data files, start counting with {first_file_number}')

    print(f'Processing {file_count} files with {args.jobs} processes:')
    process_f = partial(process_file, output_path=args.data_path)
    with multiprocessing.Pool(processes=args.jobs,
                              initializer=init_file_counter,
                              initargs=(current_file_number,)) as p:
        for file in tqdm(p.imap_unordered(process_f, file_names), total=file_count):
            pass
