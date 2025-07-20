#!/usr/bin/env python
# vim: noet ts=4 number
"""
	LST: "Local Solar Time" timezone implementation
"""
import pendulum
from datetime import timedelta
from astral import Observer
from astral.sun import sun as Sun
import time

#import numpy as np
#try:
#	import quaternion
#except ImportError as e:
#	from sys import stderr
#	print(f"{e}: package 'numpy-quaternion' is required", file=stderr)

class TimezoneLockedError(Exception):
	"""
		this exception is raised when an LST timezone is used for a "here and now" (LST.now()) datetime object ; in such
		a case it makes no sense to change the "where" or "when" so the timezone parameters cannot be updated
	"""

class RedundantCall(Exception):
	"""
		there was no point in calling the function that triggered this exception
	"""


class LST(pendulum.Timezone):
	user_events = []
	update_timedelta = timedelta(hours=3)
	_update_interval = None
	def __init__(self, pos_update_func):
		"""
			A timezone that has its UTC offset set so that the sun is at its zenith when it is noon, based on the current
			longitude.

			pos_update_func: a function that returns a tuple (or a tuple!) in the form (location_info, lat_long, alt) where:
			- location_info: a tuple of the form (region,location)
			- lat_long: a tuple of the form (latitude, longitude) where both are degrees (float)
			- alt: AMSL altitude (float) in meters

			self.update_interval: one of [s]econd, [m]inute, [h]hour, [d]ay, None (manual updates only) or False (tz is locked)
			if pos_update_func is a tuple, update_interval is automatically set to None (and that must stay None)

			TODO: exact sunrise and sunset times with angle of the horizon a the spot ; requires a function that varies throughout
			the year
		"""
		if type(pos_update_func) is tuple:
			location_info, lat_long, altitude = pos_update_func
			#self.where = LocationInfo(*location_info, 'UTC', *lat_long)
			self.location = location_info
			self.where = Observer(*lat_long, altitude)
		else:
			self._pos_update_func = pos_update_func
			self.update()

	
	def __new__(self, *args, **kwargs):
		self = super().__new__(self, 'UTC')
		return self
	
	def __str__(self):
		# err... dunno why this needs to be overriden (returns 'UTC' otherwise)
		return self.key
	
	def __repr__(self):
		return "Timezone('LST')"
	
	# NOTE: we'd like to be able to override this...
	#def __type__(self):
	#	return pendulum.tz.timezone.Timezone

	@property
	def latitude(self):
		return self._where.latitude

	@property
	def longitude(self):
		return self._where.longitude

	@property
	def lat_long(self):
		return self._where.latitude, self._where.longitude

	@lat_long.setter
	def lat_long(self, lat_long):
		self._where.latitude, self._where.longitude = lat_long

	@property
	def altitude(self):
		return self._altitude

	@altitude.setter
	def altitude(self, alt=None):
		if alt is None:
			# TODO set altitude to 0m AGL
			raise NotImplementedError("Please provide AMSL altitude")
		else:
			# NOTE: might want to check for validity..
			self._altitude = alt

	@property
	def update_interval(self):
		return self._update_interval
	
	@update_interval.setter
	def update_interval(self, value):
		if self._update_interval is False:
			raise TimezoneLockedError
		else:
			if value not in ('d','h','m','s',None,False):
				raise ValueError
			self._update_interval = value

	def convert(self, dt: '_DT', raise_on_unknown_times: 'bool' = False):# -> '_DT'
		"""
			Converts a datetime in the current timezone.

			If the datetime is naive, it will be considered as "here and now".

			Either way, the LST timezone attached to the datetime object will be locked.

			TODO: do something sensible with raise_on_unknown_times (kept for compatibility)
		"""
		if dt.tzinfo is not None:
			dt_utcoffset = dt.utcoffset()
			dt = dt.replace(tzinfo=None)-dt_utcoffset+self.utcoffset()
	
		if self._update_interval is False:
			return dt.replace(tzinfo=self)
		else:
			tz = LST((self.location, (self.where.latitude, self.where.longitude), self.where.elevation))
			return dt.replace(tzinfo=tz)
			
	
	def datetime(self, year: 'int', month: 'int', day: 'int', hour: 'int' = 0, minute: 'int' = 0, second: 'int' = 0, microsecond: 'int' = 0, tz = None):# -> '_datetime.datetime'
		"""
			returns a datetime object in LST timezone
		"""
		if tz is None:
			lst = LST(((self.where.name, self.where.region), (self.where.latitude, self.where.longitude), self.where.altitude))
			return pendulum.datetime( year, month, day, hour, minute, second, microsecond, tz=None).replace(tzinfo=lst)
		else:
			dt = pendulum.datetime( year, month, day, hour, minute, second, microsecond, tz=tz)
			utcoffset = dt.utcoffset(dt)
			return (dt.replace(tzdata=None)-utcoffset+self._noon_offset).replace(tz=lst)
	

	def dst(self, dst):
		"""
			Retrieve a timedelta representing the amount of DST applied in a zone at the given datetime:
			by definition this is always zero.
		"""
		return timedelta()
	
	#from_file(file_obj, /, key=None) class method of pendulum.tz.timezone.Timezone

	def fromutc(self, dt):
		"""
			Given a datetime with local time in UTC, retrieve an adjusted datetime in local time.

			TODO make sure this is really the expected behaviour! I'm not quite sure...
		"""
		if type(dt.tzinfo) is not type(self):
			raise ValueError("dt.tzinfo is not self")

		if self._update_interval is False:
			return dt.naive().replace(tzinfo='UTC').replace(tzinfo=self)
		else:
			lst = LST(((self.where.name, self.where.region), (self.where.latitude, self.where.longitude), self.where.altitude))
			return dt.naive().replace(tzinfo='UTC').replace(tzinfo=lst)
	
	@property
	def key(self):
		"""
		we could return '/'.join([self.where.name,self.where.region]) BUT this is likely to have collisions
		with standard timezones keys ; instead we chose to return this info in self.name
		"""
		return 'LST'
	
	@property
	def name(self):
		return '/'.join([self.where.region, self.where.name])

	# err... what does this no anyway? same for clear_cache...
	#no_cache(key) class method of pendulum.tz.timezone.Timezone

	def tzname(self, *args):
		return self.key
	
	def utcoffset(self, dt=None):
		"""
			Retrieve a timedelta representing the UTC offset in a zone at the given datetime.
			Since neither UTC nor LST have DST, dt can be safely ignored or omitted.

			NOTE: don't ignore dt if we're on another planet?
		"""
		return self._noon_offset
	

	"""
		####### non standard functions
	"""
	def now(self):
		"""
			returns a datetime object with a copy of the current timezone (locked) for "now"
		"""
		now = (pendulum.now().utcnow()+self._noon_offset)
		if self._update_interval is False:
			return now.replace(tzinfo=self)
		else:
			return now.replace(tzinfo=LST(((self.where.name, self.where.region), (self.where.latitude, self.where.longitude), self.where.altitude)))
	
	def today(self):
		"""
			returns a datetime object (timezone locked) for today very shortly after midnight
		"""
		now = self.now()
		return self.datetime(now.year, now.month, now.day, 0,0,0,0)

	def update(self, pos = None):
		"""
			update offsets based on date and position ; can be either called periodically by self (will call self.point) or
			be called externally with a 'pos' argument

			FYI: 1km on the equator is about 450[ms] offset in solar time
		"""
		if self.update_interval is False:
			raise TimezoneLockedError

		if pos is None:
			try:
				location_info, lat_long, altitude = self._pos_update_func()
				self.where = Observer(*lat_long, altitude)
				self.location = location_info
			except AttributeError:
				# location was passed as a tuple (not a function), we only allow one update)
				self.update_interval = False
		else:
			location_info, lat_long, altitude = pos
			self.where = Observer(*lat_long, altitude)
			self.location = location_info

		# TODO only update self.sun if position changed significantly (see self.pos quaternion above), or day changed
		#self.pos = np.quaternion(1., self.where.latitude, self.where.longitude, self.where.altitude)
		#self.pos.normalized()	# TODO normalize so that altitude changes are negligible
			
		# local noon offset relative to UTC
		now = pendulum.now()
		# TODO sun yesterday! this can matter.. 
		sun_tomorrow = Sun(self.where, date=now+timedelta(days=1))
		sun_today = Sun(self.where, date=now)

		noon = sun_today['noon']
		self._noon_offset = timedelta(seconds = (12-noon.hour)*3600-(noon.minute*60)-noon.second, microseconds=-noon.microsecond)
		# deleting obsolete events
		delete = [name for name, dt in sun_today.items() if dt < now-self.update_timedelta]
		for name in delete:
			sun_today.pop(name)
		self.sun = sun_tomorrow|sun_today

		# user events based on astronomical events such as muslim prayer times
		self.event_times, self.duplicate_event_names = {}, []
		for func, args, kwargs in self.user_events:
			events = func(now-self.update_timedelta, self.where.latitude, self.where.longitude, self.where.altitude, *args, **kwargs)
			self.duplicate_event_names.extend([k for k in events.keys() if k in self.event_times.keys()])
			self.event_times |= events

	
	def schedule_updates(self):
		"""
			schedule position updates

			TODO dynamically adjust interval based on computed speed based on previous lat/long/(alt) values
		"""
		import sched
	
		while True:
			self.S = sched.scheduler(time.time, time.sleep)

			# TODO use timedelta? fixed interval (ie. "at the minute", "at the hour", etc. -> round and increment) ?
			match self.update_interval:
				case False:
					raise TimezoneLockedError
				case 'd':
					self.S.enterabs(pendulum.tomorrow().timestamp()+1, 1, self.update)
				case 'h':
					self.S.enterabs(pendulum.now().timestamp()+3600, 1, self.update)
				case 'm':
					self.S.enterabs(pendulum.now().timestamp()+60, 1, self.update)
				case 's':
					self.S.enterabs(pendulum.now().timestamp()+1, 1, self.update)
				case None:
					break
				case _:
					raise ValueError

			self.S.run()
			del self.S

	def event_add(self, func, args = (), kwargs = {}):
		"""
			add user events that rely on astronomical data such as latitude, longitude and altitude and day of the year ; by
			definition such events will be recursive

			the function must accept (timedate_reference, latitude, longitude, altitude, *args, **kwargs) as arguments and 
			return a dict in the form {event_name: datetime} for the next 24 hour perdiod ; if no timezone is set to None, 
			LST will be assumed AT THE TIME OF THE UPDATE (in practice this changes very little or nothing because the
			location update will replace events with the same name). events need not be sorted by datetime.
		"""
		self.user_events.append((func, args, kwargs))
	
	def event_del(self,e):
		"""
			delete user events from the list ; argument can either be a string index or a list/tuple of string indexes
		"""
		if type(e) in (tuple, list):
			for event in e:
				self.user_events.pop(e)
		else:
			self.user_events.pop(e)
	
	def display(self):
		""" NOTE: intially for dev purposes.. keep it? """
		now = {'Now': self.now()}
		for name, dt in sorted((self.sun|self.event_times|now).items(), key=lambda item: item[1]):
			yield f"{'->' if name == 'Now' else ''}\t{name:<10}{self.convert(dt).strftime('%Y-%m-%d %H:%M:%S')}"

def dummy_location(index = None):
	# this is just an example for when GPS is unavailable. values are
	# (region, location), (latitude, longitude), altitude
	choices = ((
		(('Aiguille MIH', 'La Chaux-de-Fonds, Switzerland'), (47.10042765476871, 6.830537909805381), 1000),
		(('Great pyramid (tip)', 'Gyza, Egypt'), (29.97921992508711, 31.134201381120103), 198.8), # not sure about the altitude here
		(('Ahu Tongakiri', 'Easter Island, South Pacific Ocean'), (-27.12560731530453, -109.27671897486), 22), # not sure either about altitude
		(('Veerabhadra Temple', 'Hampi, Karnataka, India'), (15.331628235993037, 76.46830420763662), 514),
		(('Mount Everest', 'Nepal, Himalaya'), (27.988075179660846, 86.92502173497084), 8848.86),
		(('Cook Inlet', 'Anchorage, North America'), (61.126793732458395, -150.28694933121557), 0),
		(('Uluru', 'Australia'), (-25.345058743303507, 131.03162847609963), 863),	# not sure about the exact location of the highest point
		(('Molde','Norway'), (62.73874271153322, 7.181428824527326), 7),	# altitude is approximate
		(('Wombat Island','Antartica'), (-67.56257032149553, 47.77256758885169), 3),
		#(('Буустаах','Саха Өрөспүүбүлүкэтэ'), (72.52987962713195, 141.9583417089322), -1),
		(('Wadi Al Mujib delta','Jordan'),(31.466898587642135, 35.563242264958284),-439.78),
		(('Ulitsa Gubina/Ulitsa Bogatyreva','Якутск'),(62.0400620596081, 129.74801217766358),95),
	))

	if index is None:
		from random import randint
		index = randint(0,len(choices)-1)
	
	return choices[index]

if __name__ == '__main__':
	async def main(lst, delay):
		while True:
			await asyncio.sleep(delay)
			print(f"You are here: {lst.where.name} ({lst.where.region})")
			for line in lst.display():
				print(line)

	import asyncio
	from threading import Thread
	lst = LST( dummy_location )

	lst.update_interval = 's'
	T = Thread(target=lst.schedule_updates)
	T.start()

	asyncio.run(main(lst, 1))
