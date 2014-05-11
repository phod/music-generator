#---------------------
# Name: MusicGenerator.py
# Author: phod
# Intended Purpose: Implementing a genetic algorithm to procedurally generate 
# music.
# 
# Current Status: Randomly generates 5 different tracks. Can play the tracks, 
# but cannot mutate and create new generations. 
#---------------------


from midiutil.MidiFile import MIDIFile
from random import randint
from Tkinter import *
from bisect import bisect_left
from pygame import mixer, time
from threading import Thread
import threading

'''
To-Do List:
-Tidy up MenuInterface
-Create separate thread for playing music/Join() is currently buggy
-Lock the song.notes[] to prevent data race/maybe not even a problem, since the music thread wont need to access song.notes[]
-Lock file modification while music is playing.
-Clicking generate stops music and any other threads except tkinter
-Implement the fitness allocation
-Implement the genetic crossover and mutation
-Separate file into appropriate modules
-Implement rhythm into Songs
-Implement octave/rhythm mutation
'''


class MenuInterface: 
	'''
	Contains the GUI implementation, only play function currently works
	'''
	
	'''
	Initilises the GUI variables, starts GUI loop
	'''
	def __init__(self, master, count, song_length):
		#generate population and songs
		self.count = count
		self.pop = Population(count, song_length, True)
		self.mutator = Mutator(count, song_length)
		self.play_buttons = []
		self.setup_rating()
		master.mainloop()
		
	
	def setup_rating(self):
		
		MODES = [
			("Horrible", 0),
			("Bad", 1),
			("Average", 2),
			("Good", 3),
			("Amazing", 4)
		]
		self.radio_vars = []
		
		for mode, num in MODES:
			w = Label(master, text=mode).grid(row=0, column=num + 1)
		
		for j in range(0, self.count):
			v = IntVar()
			self.radio_vars.append(v)
			self.play_buttons.append(Button(master, text = "Play", command=lambda num=j: self.play(num)).grid(row = j + 1, column = 0))
			for mode, num in MODES:
				r = Radiobutton(master, variable = v, value=num).grid(row = j + 1, column = num + 1)
				
		generate_button = Button(master, text = "Generate", command=lambda: self.submit()).grid(row=self.count + 1, column=2, columnspan=3, sticky=S, padx=5, pady=5)
		
		
		
	def play(self, i):
		self.pop.play_song(i)
		
	def submit(self):
		for i in range(0,self.count):
			fitness = self.radio_vars[i].get() 
			self.pop.set_fitness(i, fitness)
		self.pop = self.mutator.evolve_population(self.pop)
	
	
class Mutator:
	
	TOURNAMENT_SIZE = 3
	MUTATION_FACTOR = 10
	
	def __init__(self, count, song_length):
		print "Hello"
		self.count = count
		self.song_length = song_length
		self.elitism = True
		
	
	def evolve_population(self, population):
		new_population = Population(self.count, self.song_length, False)
		elitism_offset = 0
		
		if self.elitism:
			elitism_offset = 1
			new_population.add_song(population.get_fittest())
		
		for i in range (0, self.count):
			indiv1 = self.tournament_selection(population)
			indiv2 = self.tournament_selection(population)
			new_indiv = self.cross_over(indiv1, indiv2)
			new_population.add_song(new_indiv)
		
		return new_population
		
	def tournament_selection(self, population):
		self.tournament_pop = Population(self.TOURNAMENT_SIZE, self.song_length, False)
		for i in range(0, self.TOURNAMENT_SIZE):
			self.tournament_pop.songs.append(population.get_song(randint(0, self.count - 1))) 
			
		fittest = self.tournament_pop.get_fittest()	
		return fittest
		
	def cross_over(self, indiv1, indiv2):
		print "Incomplete"
		return indiv1
	
	
	
class Population:
	
	def __init__(self, count, song_length, initialise):
		if initialise:
			self.songs = []
			self.count = count
			self.song_length = song_length
			for i in range(0, count):
				song = Song(song_length, i)
				self.songs.append(song)
		else:
			self.songs = []
			self.count = count
			self.song_length = song_length
		
	def add_song(self, song):
		self.songs.append(song)
		
	def get_song(self, index):
		if index <= self.count:
			return self.songs[index]
		
	def play_song(self, num):
		song_thread = threading.Thread(target=lambda: self.songs[num].play(song_thread))
		song_thread.start()
		
	def set_fitness(self, num, fitness):
		self.songs[num].fitness = fitness
		
	def get_fittest(self):
		max = -1
		for i in range(0, len(self.songs)):
			if (self.songs[i].fitness > max):
				max = self.songs[i].fitness
				fittest = self.songs[i]
		return fittest
	
class Song:
	'''
	Contains individual song information, note constants have been made just 
	in case they are required
	'''
	NOTE_C = 0
	NOTE_C_SHARP = 1
	NOTE_D = 2
	NOTE_D_SHARP = 3
	NOTE_E = 4
	NOTE_F = 5
	NOTE_F_SHARP = 6
	NOTE_G = 7
	NOTE_G_SHARP = 8
	NOTE_A = 9
	NOTE_A_SHARP = 10
	NOTE_B = 11
	
	LOWER_OCTAVE = 3
	UPPER_OCTAVE = 6
	OCTAVE_THRESHOLD = 50
		
	def __init__(self, length, id):
		self.my_MIDI = MIDIFile(1)
		self.prob = [[] for i in range(12)]
		self.totals = []
		self.notes = []
		self.prev_note = -1
		self.fitness = 0
		self.id = id
		self.length = length
		
		self.generate_prob()
		self.generate_notes(length)
		self.create(self.notes)
	
	
	def generate_prob(self):
		for i in range(0, 12):
			total = 0
			for j in range(0,12):
				num = randint(1,100) #start from 1, to ensure that a list of all 0 never occurs
				total += num
				#Implemented so probability can be calculate via int. Has an additive effect. 
				self.prob[i].insert(j, total)
				
			self.totals.insert(i, total)

			
	def generate_notes(self, length):
		octave = 0
		for i in range(0, length):
			octave = self.generate_octave(octave)
			if self.prev_note == -1:
				curr_note = randint(0,11)
				self.notes.append(curr_note + octave * 12)
				self.prev_note = curr_note
			else:
				num = randint(0, self.totals[self.prev_note])
				pos = bisect_left(self.prob[self.prev_note], num, lo=0, hi=len(self.prob[self.prev_note]))
				self.notes.append(pos + octave * 12)
				self.prev_note = pos
						
		return self.notes
		
					
	def generate_octave(self, prev_octave):
		if prev_octave == 0:
			return randint(Song.LOWER_OCTAVE, Song.UPPER_OCTAVE)
		if randint(0,100) < Song.OCTAVE_THRESHOLD:
			return prev_octave
		if prev_octave <= Song.LOWER_OCTAVE:
			return prev_octave + randint(0,1)
		elif prev_octave >= Song.UPPER_OCTAVE:
			return prev_octave - randint(0,1)
		else:
			return prev_octave + (randint(0,2) - 1)
					
	def create(self, notes):
		track = 0   
		time = 0
		channel = 0
		duration = 1
		volume = 100
		# Add track name and tempo.
		self.my_MIDI.addTrackName(track,time,"Track " + str(id))
		self.my_MIDI.addTempo(track,time,120)

		# Now add the note.
		for x in range(0,self.length):
			self.my_MIDI.addNote(track,channel,self.notes[x],x,duration,volume)
		# And write it to disk.
		binfile = open("output" + str(self.id) + ".mid", 'wb')
		self.my_MIDI.writeFile(binfile)
		binfile.close()
		
		
	'''
	need to create separate thread/tidy up function
	Most of code from http://www.daniweb.com/software-development/python/code/216976/play-a-midi-music-file-using-pygame
	'''
	def play(self, song_thread):
		music_file = "output" + str(self.id) + ".mid"
		clock = time.Clock()
		
		freq = 44100 # audio CD quality
		bitsize = -16 # unsigned 16 bit
		channels = 2 # 1 is mono, 2 is stereo
		buffer = 1024 # number of samples
		mixer.init(freq, bitsize, channels, buffer)
		
		# optional volume 0 to 1.0
		mixer.music.set_volume(0.8)

		try:
			try:
				mixer.music.load(music_file)
				print "Music file %s loaded!" % music_file
			except error:
				print "File %s not found! (%s)" % (music_file, get_error())
				return
			mixer.music.play()
			while mixer.music.get_busy():
				# check if playback has finished
				clock.tick(30)
		except KeyboardInterrupt:
			# if user hits Ctrl/C then exit
			# (works only in console mode)
			# modify to work on GUI
			mixer.music.fadeout(1000)
			mixer.music.stop()
			raise SystemExit
		song_thread.join()
		
		
										
count = 5
length = 20
master = Tk()
menu_interface = MenuInterface(master, count, length)