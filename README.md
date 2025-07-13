# Local Solar Time

This code is for a timezone object that conforms (or at least should) to a
`pendulum.Timezone()` object abbreviated `LST` ; Its purpose is to help
humanity get back in sync with nature while at the same time providing a
framework for dealing with datetimes in the context of space travel (including
outside of the Earth's troposphere).

Its property is that it relies on astronomical calculations based on the
current longitude to compute the time in such a way that *twelve o'clock* (or
*noon*) always happens when the sun is a its zenith (shortest possible daytime
shadow) and adjust the UTC offset accordingly.

There are provisions to dynamically update events that rely on the geographical
position (Muslim prayer times are an example of this, see `examples.py`).
