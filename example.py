#!/usr/sbin/env python
# vim: noet ts=4 number

"""
	The Times of the Beginning and End of the Five Daily Prayers

	Fajr (Dawn Prayer):
		From the break of true dawn (horizontal white light spreading across the horizon) until sunrise.
	
	Dhurh (Noon Prayer):
		From the time the sun passes its meridian (midday) until the shadow of a thing is equal to its length.
	
	Asr (Afternoon Prayer):
		From the time when Noon Prayer ends until the sun sets.
	
	Marghib (Sunset Prayer):
		From sunset until the disappearance of red twilight.
	
	Isha (Night Prayer):
		From the disappearance of the red twilight glow until the middle of the night.
"""
try:
	from adhanpy import PrayerTimes
except ImportError:
	print("package 'adhanpy' is not installed, PrayerTimes will be disabled", file=stderr)
	def prayertimes():
		return {}
else:
	from datetime import timedelta
	def prayertimes(timedate_reference, latitude, longitude, altitude, calculation_method = PrayerTimes.CalculationMethod.MUSLIM_WORLD_LEAGUE):
		"""
			return some prayer times

			NOTE: adhanpy accuracy is less than 60 seconds!
		"""
		# prayers tomorrow
		pt = PrayerTimes.PrayerTimes(
			(latitude, longitude), timedate_reference+timedelta(days=1), 
			calculation_method,
		)
		tomorrow = {
			"Fajr": pt.fajr,
			"Dhuhr": pt.dhuhr,
			"Asr": pt.asr,
			"Maghrib": pt.maghrib,
			"Isha": pt.isha,
		}
		# prayers today
		pt = PrayerTimes.PrayerTimes(
			(latitude, longitude), timedate_reference, 
			calculation_method,
		)
		today = {
			"Fajr": pt.fajr,
			"Dhuhr": pt.dhuhr,
			"Asr": pt.asr,
			"Maghrib": pt.maghrib,
			"Isha": pt.isha,
		}
		# removing past prayer times
		delete = [name for name, dt in today.items() if dt < timedate_reference]
		for name in delete:
			today.pop(name)
		return tomorrow|today

if __name__ == '__main__':
	from threading import Thread
	from LST import LST, dummy_location

	lst = LST( dummy_location() )
	print(f"You are here: {lst.where.name} ({lst.where.region})")

	lst.event_add(prayertimes)
	lst.update()

	for line in lst.display():
		print(line)
